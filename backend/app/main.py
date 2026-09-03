"""Application entrypoint.

Run with: ``uvicorn app.main:app --reload`` (from ``backend/``).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router, legacy_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.exceptions.handlers import register_exception_handlers
from app.middleware.middleware import RequestContextMiddleware, SecurityHeadersMiddleware

settings = get_settings()
configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    try:
        from app.db.session import check_connection

        check_connection()
        log.info("database_connected")
    except Exception as exc:
        log.warning("database_unavailable", error=str(exc))
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router)
    app.include_router(legacy_router)

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok", "app": settings.app_name,
                "environment": settings.environment}

    @app.get("/health/db", tags=["health"])
    def health_db() -> dict:
        try:
            from sqlalchemy import text

            from app.db.session import get_engine

            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "ok", "database": "reachable"}
        except Exception as exc:
            return {"status": "degraded", "database": str(exc)}

    @app.get("/health/redis", tags=["health"])
    def health_redis() -> dict:
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(settings.redis_url,
                                          socket_connect_timeout=2)
            client.ping()
            return {"status": "ok", "redis": "reachable"}
        except Exception as exc:
            return {"status": "degraded", "redis": str(exc)}

    return app


app = create_app()
