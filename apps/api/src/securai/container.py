"""Composition root / dependency-injection container.

Holds application-wide singletons (settings, database, rate limiter, LLM
provider) and knows how to assemble per-request services from a DB session.
This is the only place that wires concrete adapters to ports.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from securai.config import Settings, get_settings
from securai.modules.gateway.adapters.request_log_repo import SqlRequestLogRepo
from securai.modules.gateway.application.service import GatewayService
from securai.modules.gateway.domain.ports import LLMProvider
from securai.modules.identity.adapters.repositories import (
    SqlApiKeyRepo,
    SqlOrgRepo,
    SqlProjectRepo,
    SqlUserRepo,
)
from securai.modules.identity.application.service import IdentityService
from securai.modules.router.adapters.providers import build_provider
from securai.modules.router.application.router import ModelRouter
from securai.shared.db import Database
from securai.shared.rate_limit import SlidingWindowRateLimiter


class Container:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.database = Database(self.settings.database_url, echo=self.settings.db_echo)
        self.rate_limiter = SlidingWindowRateLimiter(
            max_per_minute=self.settings.rate_limit_per_minute
        )
        self.llm_provider: LLMProvider = build_provider(self.settings)
        self.router = ModelRouter(provider=self.llm_provider, settings=self.settings)

    # --- per-request service factories ---

    def identity_service(self, session: AsyncSession) -> IdentityService:
        return IdentityService(
            settings=self.settings,
            orgs=SqlOrgRepo(session),
            users=SqlUserRepo(session),
            projects=SqlProjectRepo(session),
            api_keys=SqlApiKeyRepo(session),
        )

    def gateway_service(self, session: AsyncSession) -> GatewayService:
        return GatewayService(
            settings=self.settings,
            router=self.router,
            request_logs=SqlRequestLogRepo(session),
        )

    async def startup(self) -> None:
        if self.settings.auto_create_schema:
            await self.database.create_all()

    async def shutdown(self) -> None:
        await self.database.dispose()
