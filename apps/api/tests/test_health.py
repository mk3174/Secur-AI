import pytest


@pytest.mark.asyncio
async def test_healthz(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readyz(client):
    resp = await client.get("/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"ready", "degraded"}
    assert body["provider"] is True  # echo provider is always healthy


@pytest.mark.asyncio
async def test_metrics_exposed(client):
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "securai_requests_total" in resp.text


@pytest.mark.asyncio
async def test_dashboard_served(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "SecurAI" in resp.text


@pytest.mark.asyncio
async def test_correlation_id_header(client):
    resp = await client.get("/healthz")
    assert resp.headers.get("x-request-id")
