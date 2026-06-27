"""Gateway outbound ports."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from securai.modules.gateway.domain.messages import (
    CanonicalChatRequest,
    CanonicalChatResponse,
    ChatChunk,
)


class LLMProvider(Protocol):
    name: str

    async def chat(self, request: CanonicalChatRequest) -> CanonicalChatResponse: ...

    def chat_stream(self, request: CanonicalChatRequest) -> AsyncIterator[ChatChunk]: ...

    async def health(self) -> bool: ...


class RequestLogRepo(Protocol):
    async def add(self, record: dict) -> None: ...
    async def list_recent(
        self, *, org_id: str, project_id: str | None, limit: int
    ) -> list[dict]: ...
    async def stats(self, *, org_id: str) -> dict: ...
