"""Management/dashboard routes: auth, projects, API keys, logs, stats."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from securai.interfaces.deps import (
    get_gateway_service,
    get_identity_service,
    require_user,
)
from securai.modules.gateway.application.service import GatewayService
from securai.modules.identity.api.schemas import (
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    CreateApiKeyRequest,
    CreateProjectRequest,
    LoginRequest,
    MeResponse,
    ProjectResponse,
    StatsResponse,
    TokenResponse,
)
from securai.modules.identity.application.service import IdentityService
from securai.modules.identity.domain.entities import Principal

auth_router = APIRouter(prefix="/auth", tags=["auth"])
mgmt_router = APIRouter(tags=["management"])


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    identity: IdentityService = Depends(get_identity_service),
) -> TokenResponse:
    token = await identity.login(email=payload.email, password=payload.password)
    return TokenResponse(
        access_token=token,
        expires_in=request.app.state.container.settings.jwt_access_ttl_seconds,
    )


@mgmt_router.get("/me", response_model=MeResponse)
async def me(principal: Principal = Depends(require_user)) -> MeResponse:
    return MeResponse(
        subject=principal.subject,
        org_id=principal.org_id,
        role=principal.role,
        auth_type=principal.auth_type,
    )


@mgmt_router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    payload: CreateProjectRequest,
    principal: Principal = Depends(require_user),
    identity: IdentityService = Depends(get_identity_service),
) -> ProjectResponse:
    IdentityService.authorize(principal, "project:manage")
    project = await identity.create_project(org_id=principal.org_id, name=payload.name)
    return ProjectResponse(id=project.id, org_id=project.org_id, name=project.name)


@mgmt_router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    principal: Principal = Depends(require_user),
    identity: IdentityService = Depends(get_identity_service),
) -> list[ProjectResponse]:
    projects = await identity.list_projects(org_id=principal.org_id)
    return [ProjectResponse(id=p.id, org_id=p.org_id, name=p.name) for p in projects]


@mgmt_router.post(
    "/projects/{project_id}/keys", response_model=ApiKeyCreatedResponse, status_code=201
)
async def create_api_key(
    project_id: str,
    payload: CreateApiKeyRequest,
    principal: Principal = Depends(require_user),
    identity: IdentityService = Depends(get_identity_service),
) -> ApiKeyCreatedResponse:
    IdentityService.authorize(principal, "key:manage")
    key, full_key = await identity.create_api_key(
        org_id=principal.org_id,
        project_id=project_id,
        name=payload.name,
        scopes=payload.scopes,
    )
    return ApiKeyCreatedResponse(
        id=key.id,
        name=key.name,
        prefix=key.prefix,
        scopes=key.scopes,
        status=key.status,
        api_key=full_key,
    )


@mgmt_router.get("/projects/{project_id}/keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    project_id: str,
    principal: Principal = Depends(require_user),
    identity: IdentityService = Depends(get_identity_service),
) -> list[ApiKeyResponse]:
    IdentityService.authorize(principal, "key:manage")
    keys = await identity.list_api_keys(project_id=project_id)
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            prefix=k.prefix,
            scopes=k.scopes,
            status=k.status,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
        )
        for k in keys
        if k.org_id == principal.org_id
    ]


@mgmt_router.post("/keys/{key_id}/revoke", status_code=204)
async def revoke_api_key(
    key_id: str,
    principal: Principal = Depends(require_user),
    identity: IdentityService = Depends(get_identity_service),
) -> None:
    IdentityService.authorize(principal, "key:manage")
    await identity.revoke_api_key(key_id=key_id, org_id=principal.org_id)


@mgmt_router.get("/logs")
async def list_logs(
    principal: Principal = Depends(require_user),
    gateway: GatewayService = Depends(get_gateway_service),
    project_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    IdentityService.authorize(principal, "logs:read")
    logs = await gateway.list_logs(
        org_id=principal.org_id, project_id=project_id, limit=limit
    )
    return {"data": logs}


@mgmt_router.get("/stats", response_model=StatsResponse)
async def stats(
    principal: Principal = Depends(require_user),
    gateway: GatewayService = Depends(get_gateway_service),
) -> StatsResponse:
    IdentityService.authorize(principal, "logs:read")
    return StatsResponse(**await gateway.stats(org_id=principal.org_id))
