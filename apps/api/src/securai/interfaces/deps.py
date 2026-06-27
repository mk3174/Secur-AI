"""FastAPI dependency providers (wiring requests to the container)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from securai.container import Container
from securai.modules.gateway.application.service import GatewayService
from securai.modules.identity.application.service import IdentityService
from securai.modules.identity.domain.entities import Principal
from securai.shared.errors import AuthenticationError


def get_container(request: Request) -> Container:
    return request.app.state.container


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    container: Container = request.app.state.container
    async with container.database._sessionmaker() as session:  # noqa: SLF001
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_identity_service(
    request: Request, session: AsyncSession = Depends(get_session)
) -> IdentityService:
    return request.app.state.container.identity_service(session)


def get_gateway_service(
    request: Request, session: AsyncSession = Depends(get_session)
) -> GatewayService:
    return request.app.state.container.gateway_service(session)


def _bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise AuthenticationError("Missing or malformed Authorization header.")
    return header[7:].strip()


async def require_api_key(
    request: Request, identity: IdentityService = Depends(get_identity_service)
) -> Principal:
    """Authenticate inference/management calls made with an API key."""
    token = _bearer_token(request)
    return await identity.authenticate_api_key(token)


async def require_user(
    request: Request, identity: IdentityService = Depends(get_identity_service)
) -> Principal:
    """Authenticate dashboard/management calls made with a JWT."""
    token = _bearer_token(request)
    return await identity.principal_from_jwt(token)
