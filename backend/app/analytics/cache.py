"""Redis cache helpers for the analytics engine (module-level functions).

Uses a module-level connection pool and falls back to an in-memory dict
when Redis is unavailable, mirroring the behaviour of
:class:`app.cache.service.CacheService`.
"""

from __future__ import annotations

import time
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

# Module-level connection pool (created once, shared across all callers).
_pool: Any = None
_pool_healthy: bool = False
_memory: dict[str, tuple[Any, float]] = {}
_MAX_MEMORY = 2000


def _get_pool() -> Any:
    """Return a shared Redis connection pool, creating it on first call."""
    global _pool, _pool_healthy
    if _pool is not None and _pool_healthy:
        return _pool
    try:
        import redis as _redis_mod

        pool = _redis_mod.ConnectionPool.from_url(
            get_settings().redis_url,
            max_connections=10,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        client = _redis_mod.Redis(connection_pool=pool)
        client.ping()
        _pool = pool
        _pool_healthy = True
        return pool
    except Exception as exc:  # noqa: BLE001
        _pool_healthy = False
        log.warning("analytics_redis_unavailable", error=str(exc))
        return None


def _client() -> Any:
    """Return a Redis client from the pool, or ``None`` if unavailable."""
    pool = _get_pool()
    if pool is None:
        return None
    try:
        import redis as _redis_mod

        return _redis_mod.Redis(connection_pool=pool)
    except Exception:  # noqa: BLE001
        return None


def cache_set(key: str, value: str, ttl: int = 300) -> None:
    client = _client()
    if client is not None:
        try:
            client.setex(key, ttl, value)
            return
        except Exception:  # noqa: BLE001,S110
            pass
    _memory[key] = (value, time.monotonic() + ttl)


def cache_get(key: str) -> str | None:
    client = _client()
    if client is not None:
        try:
            raw = client.get(key)
            if raw is not None:
                return str(raw)
            return None
        except Exception:  # noqa: BLE001,S110
            pass
    # In-memory fallback
    entry = _memory.get(key)
    if entry is None:
        return None
    value, expires = entry
    if time.monotonic() > expires:
        _memory.pop(key, None)
        return None
    return str(value)
