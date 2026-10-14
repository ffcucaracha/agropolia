from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from nats.aio.client import Client as NATS
from redis.asyncio import Redis
from sqlalchemy import text

from agropolia.auth.router import router as auth_router
from agropolia.config import get_settings
from agropolia.db import SessionFactory, engine
from agropolia.errors import install_error_handlers
from agropolia.logging import configure_logging
from agropolia.middleware import RequestContextMiddleware
from agropolia.organizations.router import router as organizations_router
from agropolia.shared.router import router as config_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.nats = None
    nc = NATS()
    try:
        await nc.connect(servers=[settings.nats_url], connect_timeout=2, max_reconnect_attempts=-1)
        app.state.nats = nc
    except Exception:
        # API may start degraded; readiness exposes unavailable async transport.
        app.state.nats = None
    yield
    await app.state.redis.aclose()
    if app.state.nats is not None:
        await app.state.nats.drain()
    await engine.dispose()


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="Agropolia API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)

    api = APIRouter(prefix="/api/v1")
    api.include_router(auth_router)
    api.include_router(organizations_router)
    api.include_router(config_router)
    app.include_router(api)

    @app.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    async def ready(response: Response):
        checks: dict[str, str] = {}
        try:
            async with SessionFactory() as db:
                await db.execute(text("SELECT 1"))
            checks["postgres"] = "ok"
        except Exception:
            checks["postgres"] = "unavailable"
        try:
            await app.state.redis.ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "unavailable"
        checks["nats"] = "ok" if app.state.nats is not None and app.state.nats.is_connected else "unavailable"
        if any(value != "ok" for value in checks.values()):
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "ok" if response.status_code == 200 else "degraded", "checks": checks}

    return app
