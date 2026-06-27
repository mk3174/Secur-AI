"""Management API schemas (dashboard / control plane)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    # Plain string: the platform must accept internal/reserved domains
    # (e.g. *.local) that strict RFC email validation rejects.
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    subject: str
    org_id: str
    role: str
    auth_type: str


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ProjectResponse(BaseModel):
    id: str
    org_id: str
    name: str


class CreateApiKeyRequest(BaseModel):
    name: str = Field(default="default", max_length=255)
    scopes: list[str] | None = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    scopes: list[str]
    status: str
    last_used_at: str | None = None


class ApiKeyCreatedResponse(ApiKeyResponse):
    api_key: str  # full secret, shown once


class StatsResponse(BaseModel):
    total_requests: int
    total_tokens: int
    total_cost_micro_usd: int
    avg_latency_ms: float
