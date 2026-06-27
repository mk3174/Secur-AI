"""OpenAI-compatible API schemas for the inference surface."""

from __future__ import annotations

import time

from pydantic import BaseModel, Field

from securai.modules.gateway.domain.messages import (
    CanonicalChatRequest,
    CanonicalChatResponse,
    ChatMessage,
)


class ChatMessageSchema(BaseModel):
    role: str = Field(pattern="^(system|user|assistant|tool)$")
    content: str


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessageSchema] = Field(min_length=1)
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    stop: list[str] | None = None
    stream: bool = False

    def to_canonical(self) -> CanonicalChatRequest:
        return CanonicalChatRequest(
            model=self.model or "",
            messages=[ChatMessage(role=m.role, content=m.content) for m in self.messages],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            stop=self.stop,
            stream=self.stream,
        )


class Choice(BaseModel):
    index: int = 0
    message: ChatMessageSchema
    finish_reason: str = "stop"


class UsageSchema(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[Choice]
    usage: UsageSchema

    @classmethod
    def from_canonical(cls, r: CanonicalChatResponse) -> ChatCompletionResponse:
        return cls(
            id=r.id,
            model=r.model,
            choices=[
                Choice(
                    index=0,
                    message=ChatMessageSchema(role="assistant", content=r.content),
                    finish_reason=r.finish_reason,
                )
            ],
            usage=UsageSchema(
                prompt_tokens=r.usage.prompt_tokens,
                completion_tokens=r.usage.completion_tokens,
                total_tokens=r.usage.total_tokens,
            ),
        )


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "securai"


class ModelList(BaseModel):
    object: str = "list"
    data: list[ModelCard]
