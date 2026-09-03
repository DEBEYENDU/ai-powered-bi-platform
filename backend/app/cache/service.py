"""Shared cache service (Redis when available, in-memory fallback).

Module-level caches (``ai/cache``, ``reports/cache``) keep their own policies;
this service is the shared connection + key-strategy helper for the rest of
the backend (datasets, ETL, analytics). Falls back to memory so the app boots
without Redis.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


class CacheService:
    def __init__(self, namespace: str = "bi", default_ttl: float = 300.0) -> None:
        self.namespace = namespace
        self.default_ttl = default_ttl
        self._redis: Any = None
        self._memory: dict = {}
        self._init_redis()

    def _init_redis(self) -> None:
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(get_settings().redis_url,
                                          socket_connect_timeout=2,
                                          decode_responses=True)
            client.ping()
            self._redis = client
        except Exception as exc:
            log.warning("redis_unavailable_fallback_memory", error=str(exc))

    def _namespaced(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    def get(self, key: str) -> Optional[Any]:
        ns = self._namespaced(key)
        if self._redis is not None:
            try:
                raw = self._redis.get(ns)
                return json.loads(raw) if raw is not None else None
            except Exception:
                pass
        entry = self._memory.get(ns)
        if entry is None:
            return None
        if (datetime.utcnow() - entry["at"]).total_seconds() > entry["ttl"]:
            del self._memory[ns]
            return None
        return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        ns, ttl = self._namespaced(key), ttl or self.default_ttl
        if self._redis is not None:
            try:
                self._redis.setex(ns, int(ttl), json.dumps(value, default=str))
                return
            except Exception:
                pass
        if len(self._memory) > 5000:
            oldest = min(self._memory, key=lambda k: self._memory[k]["at"])
            del self._memory[oldest]
        self._memory[ns] = {"value": value, "at": datetime.utcnow(), "ttl": ttl}

    def delete(self, key: str) -> None:
        ns = self._namespaced(key)
        if self._redis is not None:
            try:
                self._redis.delete(ns)
            except Exception:
                pass
        self._memory.pop(ns, None)
