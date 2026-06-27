"""SQLAlchemy implementations of identity repository ports."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from securai.modules.identity.domain.entities import ApiKey, Org, Project, User
from securai.shared.models import (
    ApiKeyModel,
    OrgModel,
    ProjectModel,
    UserModel,
)


def _org_to_entity(m: OrgModel) -> Org:
    return Org(id=m.id, name=m.name, plan=m.plan, created_at=m.created_at)


def _user_to_entity(m: UserModel) -> User:
    return User(
        id=m.id,
        org_id=m.org_id,
        email=m.email,
        password_hash=m.password_hash,
        role=m.role,
        status=m.status,
        created_at=m.created_at,
    )


def _project_to_entity(m: ProjectModel) -> Project:
    return Project(id=m.id, org_id=m.org_id, name=m.name, created_at=m.created_at)


def _key_to_entity(m: ApiKeyModel) -> ApiKey:
    return ApiKey(
        id=m.id,
        org_id=m.org_id,
        project_id=m.project_id,
        name=m.name,
        prefix=m.prefix,
        key_hash=m.key_hash,
        scopes=[s for s in m.scopes.split(",") if s],
        status=m.status,
        created_at=m.created_at,
        last_used_at=m.last_used_at,
    )


class SqlOrgRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, org: Org) -> None:
        self._s.add(OrgModel(id=org.id, name=org.name, plan=org.plan))
        await self._s.flush()

    async def get(self, org_id: str) -> Org | None:
        m = await self._s.get(OrgModel, org_id)
        return _org_to_entity(m) if m else None


class SqlUserRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, user: User) -> None:
        self._s.add(
            UserModel(
                id=user.id,
                org_id=user.org_id,
                email=user.email,
                password_hash=user.password_hash,
                role=user.role,
                status=user.status,
            )
        )
        await self._s.flush()

    async def get_by_email(self, email: str) -> User | None:
        res = await self._s.execute(select(UserModel).where(UserModel.email == email))
        m = res.scalar_one_or_none()
        return _user_to_entity(m) if m else None

    async def get(self, user_id: str) -> User | None:
        m = await self._s.get(UserModel, user_id)
        return _user_to_entity(m) if m else None


class SqlProjectRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, project: Project) -> None:
        self._s.add(ProjectModel(id=project.id, org_id=project.org_id, name=project.name))
        await self._s.flush()

    async def get(self, project_id: str) -> Project | None:
        m = await self._s.get(ProjectModel, project_id)
        return _project_to_entity(m) if m else None

    async def list_for_org(self, org_id: str) -> list[Project]:
        res = await self._s.execute(
            select(ProjectModel)
            .where(ProjectModel.org_id == org_id)
            .order_by(ProjectModel.created_at)
        )
        return [_project_to_entity(m) for m in res.scalars().all()]


class SqlApiKeyRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, key: ApiKey) -> None:
        self._s.add(
            ApiKeyModel(
                id=key.id,
                org_id=key.org_id,
                project_id=key.project_id,
                name=key.name,
                prefix=key.prefix,
                key_hash=key.key_hash,
                scopes=",".join(key.scopes),
                status=key.status,
            )
        )
        await self._s.flush()

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        res = await self._s.execute(select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash))
        m = res.scalar_one_or_none()
        return _key_to_entity(m) if m else None

    async def get(self, key_id: str) -> ApiKey | None:
        m = await self._s.get(ApiKeyModel, key_id)
        return _key_to_entity(m) if m else None

    async def list_for_project(self, project_id: str) -> list[ApiKey]:
        res = await self._s.execute(
            select(ApiKeyModel)
            .where(ApiKeyModel.project_id == project_id)
            .order_by(ApiKeyModel.created_at)
        )
        return [_key_to_entity(m) for m in res.scalars().all()]

    async def revoke(self, key_id: str) -> None:
        await self._s.execute(
            update(ApiKeyModel).where(ApiKeyModel.id == key_id).values(status="revoked")
        )

    async def touch_last_used(self, key_id: str) -> None:
        await self._s.execute(
            update(ApiKeyModel)
            .where(ApiKeyModel.id == key_id)
            .values(last_used_at=dt.datetime.now(tz=dt.UTC))
        )
