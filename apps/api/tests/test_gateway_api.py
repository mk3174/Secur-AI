import json

import pytest


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_chat_completion_openai_shape(client, api_key):
    resp = await client.post(
        "/v1/chat/completions",
        headers=bearer(api_key),
        json={"messages": [{"role": "user", "content": "hello world"}]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert "hello world" in body["choices"][0]["message"]["content"]
    assert body["usage"]["total_tokens"] >= 1
    assert body["model"] == "securai-echo-1"


@pytest.mark.asyncio
async def test_chat_requires_api_key(client):
    resp = await client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_jwt_cannot_be_used_as_api_key(client, admin_token):
    # JWT is for the dashboard, not the inference surface.
    resp = await client.post(
        "/v1/chat/completions",
        headers=bearer(admin_token),
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_validation_error_on_empty_messages(client, api_key):
    resp = await client.post(
        "/v1/chat/completions", headers=bearer(api_key), json={"messages": []}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_models(client, api_key):
    resp = await client.get("/v1/models", headers=bearer(api_key))
    assert resp.status_code == 200
    assert resp.json()["data"][0]["id"] == "securai-echo-1"


@pytest.mark.asyncio
async def test_streaming_sse(client, api_key):
    async with client.stream(
        "POST",
        "/v1/chat/completions",
        headers=bearer(api_key),
        json={"messages": [{"role": "user", "content": "one two three"}], "stream": True},
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        chunks = []
        done = False
        async for line in resp.aiter_lines():
            if not line.startswith("data:"):
                continue
            payload = line[len("data:") :].strip()
            if payload == "[DONE]":
                done = True
                break
            obj = json.loads(payload)
            delta = obj["choices"][0]["delta"].get("content", "")
            chunks.append(delta)
        assert done
        assert "".join(chunks).strip() != ""


@pytest.mark.asyncio
async def test_request_logged_and_stats(client, api_key, admin_token):
    for i in range(3):
        await client.post(
            "/v1/chat/completions",
            headers=bearer(api_key),
            json={"messages": [{"role": "user", "content": f"msg {i}"}]},
        )
    logs = (await client.get("/api/v1/logs", headers=bearer(admin_token))).json()["data"]
    assert len(logs) >= 3
    assert logs[0]["model"] == "securai-echo-1"
    assert logs[0]["status"] == "success"

    stats = (await client.get("/api/v1/stats", headers=bearer(admin_token))).json()
    assert stats["total_requests"] >= 3
    assert stats["total_tokens"] >= 3
