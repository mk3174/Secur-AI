"""LLM provider adapters implementing the gateway ``LLMProvider`` port.

- ``EchoProvider``: a deterministic mock that needs no GPU/network. It lets
  the whole platform run and be tested locally end-to-end.
- ``OpenAICompatibleProvider``: talks to any OpenAI-compatible server, which
  covers self-hosted vLLM as well as OpenAI/Anthropic-compatible gateways.

A new provider is added by writing another adapter here -- no core changes.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from securai.config import Settings
from securai.modules.gateway.domain.messages import (
    CanonicalChatRequest,
    CanonicalChatResponse,
    ChatChunk,
    Usage,
)
from securai.shared.errors import ProviderError
from securai.shared.ids import new_id


def estimate_tokens(text: str) -> int:
    """Cheap heuristic token estimate (~4 chars/token). Phase 1 placeholder."""
    if not text:
        return 0
    return max(1, len(text) // 4)


class EchoProvider:
    name = "echo"

    def __init__(self, model: str = "securai-echo-1") -> None:
        self._model = model

    def _reply(self, request: CanonicalChatRequest) -> str:
        last_user = next(
            (m.content for m in reversed(request.messages) if m.role == "user"),
            "",
        )
        return f"[echo:{request.model}] {last_user}".strip()

    async def chat(self, request: CanonicalChatRequest) -> CanonicalChatResponse:
        content = self._reply(request)
        usage = Usage(
            prompt_tokens=estimate_tokens(request.prompt_text),
            completion_tokens=estimate_tokens(content),
        )
        return CanonicalChatResponse(
            id="chatcmpl-" + new_id(), model=request.model, content=content, usage=usage
        )

    async def chat_stream(self, request: CanonicalChatRequest) -> AsyncIterator[ChatChunk]:
        content = self._reply(request)
        for token in content.split(" "):
            yield ChatChunk(content=token + " ")
        yield ChatChunk(content="", finish_reason="stop")

    async def health(self) -> bool:
        return True


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str = "",
        timeout: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport  # injectable for tests
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    def _client(self, timeout: float | None = None) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout or self._timeout, transport=self._transport)

    def _payload(self, request: CanonicalChatRequest, *, stream: bool) -> dict:
        payload: dict = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "stream": stream,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop:
            payload["stop"] = request.stop
        return payload

    async def chat(self, request: CanonicalChatRequest) -> CanonicalChatResponse:
        try:
            async with self._client() as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=self._headers,
                    json=self._payload(request, stream=False),
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"Upstream provider returned {exc.response.status_code}.",
                detail={"body": exc.response.text[:500]},
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Upstream provider request failed: {exc}") from exc

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage_raw = data.get("usage") or {}
        return CanonicalChatResponse(
            id=data.get("id", "chatcmpl-" + new_id()),
            model=data.get("model", request.model),
            content=message.get("content", ""),
            usage=Usage(
                prompt_tokens=usage_raw.get("prompt_tokens", 0),
                completion_tokens=usage_raw.get("completion_tokens", 0),
            ),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def chat_stream(self, request: CanonicalChatRequest) -> AsyncIterator[ChatChunk]:
        try:
            async with self._client() as client, client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._headers,
                json=self._payload(request, stream=True),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        yield ChatChunk(content="", finish_reason="stop")
                        return
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choice = (obj.get("choices") or [{}])[0]
                    delta = choice.get("delta") or {}
                    content = delta.get("content") or ""
                    finish = choice.get("finish_reason")
                    if content or finish:
                        yield ChatChunk(content=content, finish_reason=finish)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Upstream streaming failed: {exc}") from exc

    async def health(self) -> bool:
        try:
            async with self._client(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/models", headers=self._headers)
                return resp.status_code < 500
        except httpx.HTTPError:
            return False


def build_provider(settings: Settings):
    if settings.default_provider == "openai_compatible":
        return OpenAICompatibleProvider(
            base_url=settings.provider_base_url,
            api_key=settings.provider_api_key,
            timeout=settings.provider_timeout_seconds,
        )
    return EchoProvider(model=settings.default_model)
