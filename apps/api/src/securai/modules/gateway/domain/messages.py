"""Provider-agnostic canonical request/response types.

The gateway maps incoming OpenAI-compatible payloads into these canonical
types so the rest of the system never depends on a specific provider format.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class CanonicalChatRequest:
    model: str
    messages: list[ChatMessage]
    temperature: float = 1.0
    max_tokens: int | None = None
    stream: bool = False
    top_p: float | None = None
    stop: list[str] | None = None
    extra: dict = field(default_factory=dict)

    @property
    def prompt_text(self) -> str:
        return "\n".join(f"{m.role}: {m.content}" for m in self.messages)


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class CanonicalChatResponse:
    id: str
    model: str
    content: str
    usage: Usage
    finish_reason: str = "stop"


@dataclass
class ChatChunk:
    """A streamed delta."""

    content: str
    finish_reason: str | None = None
