"""Identity application service (use cases).

Orchestrates orgs, users, projects and API keys. Depends only on domain
ports, so it is fully unit-testable with in-memory repositories.
"""

from __future__ import annotations

from securai.config import Settings
from securai.modules.identity.domain.entities import (
    ApiKey,
    Org,
    Principal,
    Project,
    User,
    role_can,
)
from securai.modules.identity.domain.ports import (
    ApiKeyRepo,
    OrgRepo,
    ProjectRepo,
    UserRepo,
)
from securai.shared.errors import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
)
from securai.shared.ids import new_id
from securai.shared.security import (
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)


class IdentityService:
    def __init__(
        self,
        *,
        settings: Settings,
        orgs: OrgRepo,
        users: UserRepo,
        projects: ProjectRepo,
        api_keys: ApiKeyRepo,
    ) -> None:
        self._settings = settings
        self._orgs = orgs
        self._users = users
        self._projects = projects
        self._api_keys = api_keys

    # --- Provisioning ---

    async def create_org(self, name: str, *, plan: str = "free") -> Org:
        org = Org(id=new_id(), name=name, plan=plan)
        await self._orgs.add(org)
        return org

    async def create_user(
        self, *, org_id: str, email: str, password: str, role: str = "org_admin"
    ) -> User:
        if await self._users.get_by_email(email):
            raise ConflictError("A user with this email already exists.")
        user = User(
            id=new_id(),
            org_id=org_id,
            email=email,
            password_hash=hash_password(password),
            role=role,
        )
        await self._users.add(user)
        return user

    async def create_project(self, *, org_id: str, name: str) -> Project:
        project = Project(id=new_id(), org_id=org_id, name=name)
        await self._projects.add(project)
        return project

    async def list_projects(self, *, org_id: str) -> list[Project]:
        return await self._projects.list_for_org(org_id)

    async def create_api_key(
        self,
        *,
        org_id: str,
        project_id: str,
        name: str = "default",
        scopes: list[str] | None = None,
    ) -> tuple[ApiKey, str]:
        project = await self._projects.get(project_id)
        if project is None or project.org_id != org_id:
            raise NotFoundError("Project not found.")
        full_key, prefix, key_hash = generate_api_key(self._settings.api_key_prefix)
        key = ApiKey(
            id=new_id(),
            org_id=org_id,
            project_id=project_id,
            name=name,
            prefix=prefix,
            key_hash=key_hash,
            scopes=scopes or ["inference:write"],
        )
        await self._api_keys.add(key)
        return key, full_key  # full_key shown once

    async def list_api_keys(self, *, project_id: str) -> list[ApiKey]:
        return await self._api_keys.list_for_project(project_id)

    async def revoke_api_key(self, *, key_id: str, org_id: str) -> None:
        key = await self._api_keys.get(key_id)
        if key is None or key.org_id != org_id:
            raise NotFoundError("API key not found.")
        await self._api_keys.revoke(key_id)

    # --- Authentication ---

    async def authenticate_api_key(self, full_key: str) -> Principal:
        key = await self._api_keys.get_by_hash(hash_api_key(full_key))
        if key is None or key.status != "active":
            raise AuthenticationError("Invalid or revoked API key.")
        await self._api_keys.touch_last_used(key.id)
        return Principal(
            org_id=key.org_id,
            project_id=key.project_id,
            role="developer",
            scopes=key.scopes,
            subject=key.id,
            auth_type="api_key",
            api_key_id=key.id,
        )

    async def login(self, *, email: str, password: str) -> str:
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")
        if user.status != "active":
            raise AuthenticationError("User is not active.")
        return create_access_token(
            subject=user.id,
            secret=self._settings.jwt_secret,
            algorithm=self._settings.jwt_algorithm,
            ttl_seconds=self._settings.jwt_access_ttl_seconds,
            claims={"org_id": user.org_id, "role": user.role, "email": user.email},
        )

    async def principal_from_jwt(self, token: str) -> Principal:
        try:
            payload = decode_access_token(
                token,
                secret=self._settings.jwt_secret,
                algorithm=self._settings.jwt_algorithm,
            )
        except Exception as exc:  # noqa: BLE001
            raise AuthenticationError("Invalid or expired token.") from exc
        return Principal(
            org_id=payload["org_id"],
            project_id=None,
            role=payload.get("role", "viewer"),
            scopes=["*"],
            subject=payload["sub"],
            auth_type="jwt",
        )

    # --- Authorization ---

    @staticmethod
    def authorize(principal: Principal, action: str) -> None:
        if principal.auth_type == "api_key":
            if "*" in principal.scopes or action in principal.scopes:
                return
            # API keys also honour role-based defaults for read actions.
            if action == "logs:read" and "inference:write" in principal.scopes:
                return
            raise AuthorizationError(f"API key lacks scope for '{action}'.")
        if not role_can(principal.role, action):
            raise AuthorizationError(f"Role '{principal.role}' cannot perform '{action}'.")
