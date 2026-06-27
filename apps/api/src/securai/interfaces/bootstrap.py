"""First-run bootstrap: ensure a default org, admin user and project exist.

Convenience for the MVP so the platform is usable immediately. In production
this is replaced by an explicit onboarding/invite flow.
"""

from __future__ import annotations

from securai.container import Container
from securai.shared.logging import get_logger

logger = get_logger("securai.bootstrap")


async def run_bootstrap(container: Container) -> None:
    settings = container.settings
    if not settings.bootstrap_enabled:
        return

    async with container.database._sessionmaker() as session:  # noqa: SLF001
        identity = container.identity_service(session)
        existing = await identity._users.get_by_email(settings.bootstrap_admin_email)  # noqa: SLF001
        if existing is not None:
            return

        org = await identity.create_org(settings.bootstrap_org_name)
        await identity.create_user(
            org_id=org.id,
            email=settings.bootstrap_admin_email,
            password=settings.bootstrap_admin_password,
            role="org_admin",
        )
        await identity.create_project(org_id=org.id, name=settings.bootstrap_project_name)
        await session.commit()
        logger.info(
            "bootstrap_complete",
            org=settings.bootstrap_org_name,
            admin=settings.bootstrap_admin_email,
        )
