import pytest


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_login_success_and_me(client, admin_token):
    resp = await client.get("/api/v1/me", headers=bearer(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "org_admin"
    assert body["auth_type"] == "jwt"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@securai.local", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_default_project_created_by_bootstrap(client, admin_token):
    resp = await client.get("/api/v1/projects", headers=bearer(admin_token))
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) == 1
    assert projects[0]["name"] == "default"


@pytest.mark.asyncio
async def test_create_project_and_key_lifecycle(client, admin_token):
    # create project
    resp = await client.post(
        "/api/v1/projects", headers=bearer(admin_token), json={"name": "proj-a"}
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # create key (full secret shown once)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/keys",
        headers=bearer(admin_token),
        json={"name": "ci"},
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["api_key"].startswith("sk_securai_")
    key_id = created["id"]

    # list keys (no secret returned)
    resp = await client.get(
        f"/api/v1/projects/{project_id}/keys", headers=bearer(admin_token)
    )
    assert resp.status_code == 200
    keys = resp.json()
    assert keys[0]["status"] == "active"
    assert "api_key" not in keys[0]

    # revoke
    resp = await client.post(f"/api/v1/keys/{key_id}/revoke", headers=bearer(admin_token))
    assert resp.status_code == 204

    resp = await client.get(
        f"/api/v1/projects/{project_id}/keys", headers=bearer(admin_token)
    )
    assert resp.json()[0]["status"] == "revoked"


@pytest.mark.asyncio
async def test_revoked_key_cannot_authenticate(client, admin_token):
    projects = (await client.get("/api/v1/projects", headers=bearer(admin_token))).json()
    project_id = projects[0]["id"]
    created = (
        await client.post(
            f"/api/v1/projects/{project_id}/keys",
            headers=bearer(admin_token),
            json={"name": "temp"},
        )
    ).json()
    full_key = created["api_key"]

    # works before revoke
    ok = await client.post(
        "/v1/chat/completions",
        headers=bearer(full_key),
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert ok.status_code == 200

    await client.post(f"/api/v1/keys/{created['id']}/revoke", headers=bearer(admin_token))

    denied = await client.post(
        "/v1/chat/completions",
        headers=bearer(full_key),
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert denied.status_code == 401
