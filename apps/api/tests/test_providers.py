import httpx
import pytest

from securai.modules.gateway.domain.messages import CanonicalChatRequest, ChatMessage
from securai.modules.router.adapters.providers import (
    EchoProvider,
    OpenAICompatibleProvider,
    estimate_tokens,
)


def _req(content="hello", stream=False):
    return CanonicalChatRequest(
        model="m", messages=[ChatMessage(role="user", content=content)], stream=stream
    )


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("a") == 1
    assert estimate_tokens("a" * 40) == 10


@pytest.mark.asyncio
async def test_echo_chat():
    provider = EchoProvider()
    resp = await provider.chat(_req("ping"))
    assert "ping" in resp.content
    assert resp.usage.total_tokens >= 1
    assert await provider.health() is True


@pytest.mark.asyncio
async def test_echo_stream():
    provider = EchoProvider()
    chunks = [c async for c in provider.chat_stream(_req("a b c"))]
    assert any(c.finish_reason == "stop" for c in chunks)
    text = "".join(c.content for c in chunks)
    assert "a" in text and "b" in text


@pytest.mark.asyncio
async def test_openai_compatible_chat_parses_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-x",
                "model": "remote-model",
                "choices": [
                    {"message": {"role": "assistant", "content": "world"}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            },
        )

    provider = OpenAICompatibleProvider(
        base_url="http://upstream/v1", transport=httpx.MockTransport(handler)
    )
    resp = await provider.chat(_req("hi"))
    assert resp.content == "world"
    assert resp.model == "remote-model"
    assert resp.usage.prompt_tokens == 5
    assert resp.usage.completion_tokens == 2


@pytest.mark.asyncio
async def test_openai_compatible_error_maps_to_provider_error():
    from securai.shared.errors import ProviderError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    provider = OpenAICompatibleProvider(
        base_url="http://upstream/v1", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(ProviderError):
        await provider.chat(_req("hi"))
