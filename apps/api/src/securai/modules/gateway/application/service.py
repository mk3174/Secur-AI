"""Gateway application service.

Owns the request hot path: route -> call provider -> account -> log.
Phase 3 inserts the prompt firewall before/after the provider call; Phase 2
inserts caching and fallback inside the router. Those are clean extensions of
this flow.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

from securai.config import Settings
from securai.modules.gateway.domain.messages import (
    CanonicalChatRequest,
    CanonicalChatResponse,
    ChatChunk,
)
from securai.modules.gateway.domain.ports import RequestLogRepo
from securai.modules.identity.domain.entities import Principal
from securai.modules.router.adapters.providers import estimate_tokens
from securai.modules.router.application.router import ModelRouter
from securai.shared.context import get_request_id
from securai.shared.ids import new_id
from securai.shared.logging import get_logger
from securai.shared.metrics import REQUEST_COUNT, REQUEST_LATENCY, TOKENS_TOTAL

logger = get_logger("securai.gateway")

_PREVIEW_LEN = 2000


class GatewayService:
    def __init__(
        self,
        *,
        settings: Settings,
        router: ModelRouter,
        request_logs: RequestLogRepo,
    ) -> None:
        self._settings = settings
        self._router = router
        self._logs = request_logs

    def _preview(self, text: str) -> str | None:
        if not self._settings.log_prompt_content:
            return None
        return text[:_PREVIEW_LEN]

    async def _persist_log(self, record: dict) -> None:
        try:
            await self._logs.add(record)
        except Exception as exc:  # noqa: BLE001 - logging must never break the request
            logger.warning("request_log_persist_failed", error=str(exc))

    async def chat(
        self, *, request: CanonicalChatRequest, principal: Principal
    ) -> CanonicalChatResponse:
        decision = self._router.select(request.model)
        request.model = decision.model
        started = time.perf_counter()
        status = "success"
        status_code = 200
        error: str | None = None
        response: CanonicalChatResponse | None = None
        try:
            response = await decision.provider.chat(request)
            return response
        except Exception as exc:  # noqa: BLE001
            status = "error"
            status_code = getattr(exc, "status_code", 502)
            error = str(exc)
            raise
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            await self._record(
                request=request,
                principal=principal,
                response=response,
                endpoint="chat.completions",
                streamed=False,
                latency_ms=latency_ms,
                status=status,
                status_code=status_code,
                error=error,
            )

    async def chat_stream(
        self, *, request: CanonicalChatRequest, principal: Principal
    ) -> AsyncIterator[ChatChunk]:
        decision = self._router.select(request.model)
        request.model = decision.model
        started = time.perf_counter()
        collected: list[str] = []
        finish_reason = "stop"
        status = "success"
        status_code = 200
        error: str | None = None
        try:
            async for chunk in decision.provider.chat_stream(request):
                if chunk.content:
                    collected.append(chunk.content)
                if chunk.finish_reason:
                    finish_reason = chunk.finish_reason
                yield chunk
        except Exception as exc:  # noqa: BLE001
            status = "error"
            status_code = getattr(exc, "status_code", 502)
            error = str(exc)
            raise
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            content = "".join(collected)
            from securai.modules.gateway.domain.messages import CanonicalChatResponse, Usage

            synthetic = CanonicalChatResponse(
                id="chatcmpl-" + new_id(),
                model=request.model,
                content=content,
                usage=Usage(
                    prompt_tokens=estimate_tokens(request.prompt_text),
                    completion_tokens=estimate_tokens(content),
                ),
                finish_reason=finish_reason,
            )
            await self._record(
                request=request,
                principal=principal,
                response=synthetic if status == "success" else None,
                endpoint="chat.completions",
                streamed=True,
                latency_ms=latency_ms,
                status=status,
                status_code=status_code,
                error=error,
            )

    async def _record(
        self,
        *,
        request: CanonicalChatRequest,
        principal: Principal,
        response: CanonicalChatResponse | None,
        endpoint: str,
        streamed: bool,
        latency_ms: int,
        status: str,
        status_code: int,
        error: str | None,
    ) -> None:
        usage = response.usage if response else None
        cost = self._router.annotate_cost(response) if response else 0
        model = response.model if response else request.model
        provider = self._router.provider_name

        REQUEST_COUNT.labels(endpoint, provider, model, status).inc()
        REQUEST_LATENCY.labels(endpoint, provider).observe(latency_ms / 1000)
        if usage:
            TOKENS_TOTAL.labels(model, "prompt").inc(usage.prompt_tokens)
            TOKENS_TOTAL.labels(model, "completion").inc(usage.completion_tokens)

        record = {
            "id": new_id(),
            "request_id": get_request_id(),
            "org_id": principal.org_id,
            "project_id": principal.project_id or "-",
            "api_key_id": principal.api_key_id,
            "model": model,
            "provider": provider,
            "endpoint": endpoint,
            "status": status,
            "status_code": status_code,
            "streamed": streamed,
            "latency_ms": latency_ms,
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
            "cost_micro_usd": cost,
            "prompt_preview": self._preview(request.prompt_text),
            "completion_preview": self._preview(response.content) if response else None,
            "error": error,
        }
        await self._persist_log(record)
        logger.info(
            "inference_request",
            endpoint=endpoint,
            provider=provider,
            model=model,
            status=status,
            streamed=streamed,
            latency_ms=latency_ms,
            total_tokens=record["total_tokens"],
            org_id=principal.org_id,
            project_id=principal.project_id,
        )

    async def list_logs(
        self, *, org_id: str, project_id: str | None = None, limit: int = 50
    ) -> list[dict]:
        return await self._logs.list_recent(org_id=org_id, project_id=project_id, limit=limit)

    async def stats(self, *, org_id: str) -> dict:
        return await self._logs.stats(org_id=org_id)
