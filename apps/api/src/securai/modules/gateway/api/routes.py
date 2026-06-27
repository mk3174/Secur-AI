"""OpenAI-compatible inference routes (the gateway surface)."""

from __future__ import annotations

import json
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from securai.interfaces.deps import get_gateway_service, require_api_key
from securai.modules.gateway.api.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelCard,
    ModelList,
)
from securai.modules.gateway.application.service import GatewayService
from securai.modules.identity.application.service import IdentityService
from securai.modules.identity.domain.entities import Principal
from securai.shared.errors import RateLimitError
from securai.shared.ids import new_id
from securai.shared.metrics import RATE_LIMITED

router = APIRouter(tags=["inference"])


def _enforce_rate_limit(request: Request, principal: Principal) -> None:
    container = request.app.state.container
    if not container.settings.rate_limit_enabled:
        return
    key = principal.project_id or principal.org_id
    allowed, retry_after = container.rate_limiter.allow(key)
    if not allowed:
        RATE_LIMITED.labels(key).inc()
        raise RateLimitError(
            "Rate limit exceeded.", detail={"retry_after_seconds": retry_after}
        )


@router.get("/models", response_model=ModelList)
async def list_models(
    request: Request, principal: Principal = Depends(require_api_key)
) -> ModelList:
    settings = request.app.state.container.settings
    return ModelList(data=[ModelCard(id=settings.default_model)])


@router.post("/chat/completions")
async def chat_completions(
    payload: ChatCompletionRequest,
    request: Request,
    principal: Principal = Depends(require_api_key),
    gateway: GatewayService = Depends(get_gateway_service),
):
    IdentityService.authorize(principal, "inference:write")
    _enforce_rate_limit(request, principal)
    canonical = payload.to_canonical()

    if not payload.stream:
        response = await gateway.chat(request=canonical, principal=principal)
        return ChatCompletionResponse.from_canonical(response)

    completion_id = "chatcmpl-" + new_id()
    created = int(time.time())

    async def event_stream():
        model = canonical.model or request.app.state.container.settings.default_model
        async for chunk in gateway.chat_stream(request=canonical, principal=principal):
            data = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": ({"content": chunk.content} if chunk.content else {}),
                        "finish_reason": chunk.finish_reason,
                    }
                ],
            }
            yield f"data: {json.dumps(data)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
