"""Application factory and ASGI entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from securai import __version__
from securai.config import Settings, get_settings
from securai.container import Container
from securai.interfaces.bootstrap import run_bootstrap
from securai.interfaces.dashboard import DASHBOARD_HTML
from securai.interfaces.errors import register_exception_handlers
from securai.interfaces.middleware import CorrelationIdMiddleware
from securai.modules.gateway.api.routes import router as inference_router
from securai.modules.identity.api.routes import auth_router, mgmt_router
from securai.shared.logging import configure_logging, get_logger

logger = get_logger("securai")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(level=settings.log_level, json=settings.log_json)
    container = Container(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await container.startup()
        await run_bootstrap(container)
        logger.info(
            "startup_complete",
            environment=settings.environment,
            provider=container.llm_provider.name,
            version=__version__,
        )
        yield
        await container.shutdown()

    app = FastAPI(
        title="SecurAI API",
        version=__version__,
        description="SecurAI control plane - Phase 1 MVP (secure AI gateway).",
        lifespan=lifespan,
    )
    app.state.container = container

    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)

    # OpenAI-compatible inference surface
    app.include_router(inference_router, prefix="/v1")
    # Management/dashboard surface
    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(mgmt_router, prefix=settings.api_v1_prefix)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/readyz", include_in_schema=False)
    async def readyz(request: Request) -> dict:
        c: Container = request.app.state.container
        provider_ok = await c.router.health()
        return {"status": "ready" if provider_ok else "degraded", "provider": provider_ok}

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard() -> HTMLResponse:
        return HTMLResponse(DASHBOARD_HTML)

    return app


app = create_app()
