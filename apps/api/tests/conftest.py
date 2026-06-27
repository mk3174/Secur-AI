"""Shared pytest fixtures.

Each test gets an isolated app backed by an in-memory SQLite database so the
full stack (routing, auth, logging) runs without external services.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from securai.config import Settings
from securai.main import create_app


def _make_settings(**overrides) -> Settings:
    db_path = Path(tempfile.gettempdir()) / f"securai_test_{uuid.uuid4().hex}.db"
    base = dict(
        environment="local",
        database_url=f"sqlite+aiosqlite:///{db_path}",
        jwt_secret="test-secret-test-secret-test-secret-32+",
        default_provider="echo",
        default_model="securai-echo-1",
        log_json=False,
        log_level="WARNING",
        bootstrap_enabled=True,
        bootstrap_admin_email="admin@securai.local",
        bootstrap_admin_password="admin12345",
        rate_limit_per_minute=1000,
    )
    base.update(overrides)
    return Settings(**base)


@pytest_asyncio.fixture
async def app_settings() -> Settings:
    return _make_settings()


@pytest_asyncio.fixture
async def client(app_settings):
    app = create_app(app_settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Trigger lifespan (startup/bootstrap) manually for ASGITransport.
        async with app.router.lifespan_context(app):
            yield c


@pytest_asyncio.fixture
async def admin_token(client) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@securai.local", "password": "admin12345"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def api_key(client, admin_token) -> str:
    projects = (await client.get("/api/v1/projects", headers=_bearer(admin_token))).json()
    project_id = projects[0]["id"]
    resp = await client.post(
        f"/api/v1/projects/{project_id}/keys",
        headers=_bearer(admin_token),
        json={"name": "test"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["api_key"]


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
