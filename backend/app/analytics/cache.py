"""Redis cache helpers for the analytics engine (module-level functions)."""

from __future__ import annotations

import redis

from app.core.config import get_settings


def _client() -> redis.Redis:
    return redis.from_url(get_settings().redis_url, decode_responses=True)


def cache_set(key: str, value: str, ttl: int = 300) -> None:
    _client().setex(key, ttl, value)


def cache_get(key: str) -> str | None:
    value = _client().get(key)
    return str(value) if value is not None else None
