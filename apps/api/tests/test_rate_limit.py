import pytest
from httpx import ASGITransport, AsyncClient

from securai.main import create_app
from securai.shared.rate_limit import SlidingWindowRateLimiter
from tests.conftest import _make_settings


def test_sliding_window_limits():
    rl = SlidingWindowRateLimiter(max_per_minute=2)
    assert rl.allow("k")[0] is True
    assert rl.allow("k")[0] is True
    allowed, retry = rl.allow("k")
    assert allowed is False
    assert retry >= 1
    # different key is independent
    assert rl.allow("other")[0] is True


@pytest.mark.asyncio
async def test_gateway_returns_429_when_limited():
    settings = _make_settings(rate_limit_per_minute=2)
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token = (
                await client.post(
                    "/api/v1/auth/login",
                    json={"email": "admin@securai.local", "password": "admin12345"},
                )
            ).json()["access_token"]
            h = {"Authorization": f"Bearer {token}"}
            projects = (await client.get("/api/v1/projects", headers=h)).json()
            key = (
                await client.post(
                    f"/api/v1/projects/{projects[0]['id']}/keys",
                    headers=h,
                    json={"name": "rl"},
                )
            ).json()["api_key"]
            kh = {"Authorization": f"Bearer {key}"}
            body = {"messages": [{"role": "user", "content": "x"}]}

            assert (await client.post("/v1/chat/completions", headers=kh, json=body)).status_code == 200
            assert (await client.post("/v1/chat/completions", headers=kh, json=body)).status_code == 200
            limited = await client.post("/v1/chat/completions", headers=kh, json=body)
            assert limited.status_code == 429
            assert "Retry-After" in limited.headers
