"""Identity domain entities (framework-free dataclasses)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

VALID_ROLES = {
    "org_admin",
    "project_admin",
    "developer",
    "security_admin",
    "billing_admin",
    "viewer",
}

# Action -> roles allowed to perform it (minimal RBAC for Phase 1).
ROLE_ACTIONS: dict[str, set[str]] = {
    "org:manage": {"org_admin"},
    "project:manage": {"org_admin", "project_admin"},
    "key:manage": {"org_admin", "project_admin", "developer"},
    "inference:write": {"org_admin", "project_admin", "developer"},
    "logs:read": {"org_admin", "project_admin", "developer", "security_admin", "viewer"},
}


@dataclass
class Org:
    id: str
    name: str
    plan: str = "free"
    created_at: dt.datetime | None = None


@dataclass
class User:
    id: str
    org_id: str
    email: str
    password_hash: str
    role: str = "org_admin"
    status: str = "active"
    created_at: dt.datetime | None = None


@dataclass
class Project:
    id: str
    org_id: str
    name: str
    created_at: dt.datetime | None = None


@dataclass
class ApiKey:
    id: str
    org_id: str
    project_id: str
    name: str
    prefix: str
    key_hash: str
    scopes: list[str] = field(default_factory=lambda: ["inference:write"])
    status: str = "active"
    created_at: dt.datetime | None = None
    last_used_at: dt.datetime | None = None


@dataclass
class Principal:
    """The authenticated caller resolved on each request."""

    org_id: str
    project_id: str | None
    role: str
    scopes: list[str]
    subject: str  # user id or api key id
    auth_type: str  # "api_key" | "jwt"
    api_key_id: str | None = None


def role_can(role: str, action: str) -> bool:
    allowed = ROLE_ACTIONS.get(action)
    if allowed is None:
        return False
    return role in allowed
