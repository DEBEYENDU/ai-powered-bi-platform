"""Database engine, session factory, and FastAPI dependencies.

The engine is created lazily (no connection at import time) so unit tests and
docs builds work without a database. ``check_connection`` with retry is called
from the app startup event; ``get_db`` is the per-request dependency routers
use; ``get_db_session`` is a context manager for workers/jobs.
"""

from __future__ import annotations

import time
from collections.abc import Generator, Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        # Bound TCP connects: without connect_timeout a wedged database hangs
        # workers (and health checks) indefinitely. Only valid for pg drivers.
        connect_args: dict = (
            {"connect_timeout": 5} if settings.database_url.startswith("postgresql") else {}
        )
        _engine = create_engine(
            settings.database_url, pool_pre_ping=True, future=True, connect_args=connect_args
        )
        _SessionLocal = sessionmaker(
            bind=_engine, autoflush=False, autocommit=False, class_=Session, expire_on_commit=False
        )
    return _engine


# Backwards-compatible module attributes (bound on first use).
class _LazyEngine:
    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        return getattr(get_engine(), name)


class _LazySession:
    def __call__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        get_engine()
        if _SessionLocal is None:
            raise RuntimeError("Session factory not initialized")
        return _SessionLocal(*args, **kwargs)

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        get_engine()
        if _SessionLocal is None:
            raise RuntimeError("Session factory not initialized")
        return getattr(_SessionLocal, name)


engine = _LazyEngine()  # type: ignore[assignment]
SessionLocal = _LazySession()  # type: ignore[assignment]


def check_connection(retries: int = 10) -> None:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:
            last_error = exc
            log.warning("db_connect_retry", attempt=attempt, error=str(exc))
            time.sleep(min(2**attempt, 30))
    raise RuntimeError(f"Could not connect to database: {last_error}")


def get_db() -> Generator[Session, None, None]:
    get_engine()
    if _SessionLocal is None:
        raise RuntimeError("Session factory not initialized")
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Iterator[Session]:
    get_engine()
    if _SessionLocal is None:
        raise RuntimeError("Session factory not initialized")
    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
