"""Database engine, session factory, and FastAPI dependencies.

The engine is created lazily (no connection at import time) so unit tests and
docs builds work without a database. ``check_connection`` with retry is called
from the app startup event; ``get_db`` is the per-request dependency routers
use; ``get_db_session`` is a context manager for workers/jobs.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Generator, Iterator, Optional

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False,
                                     class_=Session, expire_on_commit=False)
    return _engine


# Backwards-compatible module attributes (bound on first use).
class _LazyEngine:
    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        return getattr(get_engine(), name)


class _LazySession:
    def __call__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        get_engine()
        assert _SessionLocal is not None
        return _SessionLocal(*args, **kwargs)

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        get_engine()
        assert _SessionLocal is not None
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
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"Could not connect to database: {last_error}")


def get_db() -> Generator[Session, None, None]:
    get_engine()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Iterator[Session]:
    get_engine()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
