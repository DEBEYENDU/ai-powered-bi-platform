"""Shared cache service (Redis when available, in-memory fallback).

Module-level caches (``ai/cache``, ``reports/cache``) keep their own policies;
this service is the shared connection + key-strategy helper for the rest of
the backend (datasets, ETL, analytics). Falls back to memory so the app boots
without Redis.
"""

from __future__ import annotations

import json
import time
import weakref
from typing import Any, ClassVar

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

# Circuit-breaker: after this many consecutive Redis failures, stop trying
# for a short cooldown period.
_FAIL_THRESHOLD = 5
_COOLDOWN_SECS = 30.0


class CacheService:
    # Live hit/miss counters (per instance) + registry for aggregation.
    # Weak references: instances never leak via the registry.
    _registry: ClassVar[weakref.WeakSet] = weakref.WeakSet()

    def __init__(self, namespace: str = "bi", default_ttl: float = 300.0) -> None:
        self.namespace = namespace
        self.default_ttl = default_ttl
        self._redis: Any = None
        self._memory: dict = {}
        self.hits = 0
        self.misses = 0
        self._consecutive_failures = 0
        self._circuit_open_at: float = 0.0
        self._init_redis()
        CacheService._registry.add(self)

    @classmethod
    def total_hits(cls) -> int:
        return sum(getattr(c, "hits", 0) for c in cls._registry)

    @classmethod
    def total_misses(cls) -> int:
        return sum(getattr(c, "misses", 0) for c in cls._registry)

    @classmethod
    def hit_rate(cls) -> float:
        hits, misses = cls.total_hits(), cls.total_misses()
        total = hits + misses
        return round(hits / total, 4) if total else 0.0

    def _init_redis(self) -> None:
        try:
            import redis  # type: ignore

            from app.core.net import tcp_reachable

            # Skip the ~4s redis-py retry loop when nothing is listening.
            reachable, where = tcp_reachable(get_settings().redis_url, 0.3)
            if not reachable:
                log.warning("redis_unavailable_fallback_memory", error=where)
                return
            client = redis.Redis.from_url(
                get_settings().redis_url, socket_connect_timeout=2, decode_responses=True
            )
            client.ping()
            self._redis = client
        except Exception as exc:
            log.warning("redis_unavailable_fallback_memory", error=str(exc))

    def _namespaced(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    def _redis_available(self) -> bool:
        """Check if Redis is usable (circuit breaker pattern)."""
        if self._redis is None:
            return False
        if self._consecutive_failures >= _FAIL_THRESHOLD:
            if time.monotonic() - self._circuit_open_at < _COOLDOWN_SECS:
                return False
            # Cooldown expired — try once.
            self._consecutive_failures = 0
        return True

    def _record_redis_success(self) -> None:
        self._consecutive_failures = 0

    def _record_redis_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= _FAIL_THRESHOLD:
            self._circuit_open_at = time.monotonic()
            log.warning(
                "redis_circuit_open",
                namespace=self.namespace,
                failures=self._consecutive_failures,
            )

    def get(self, key: str) -> Any | None:
        ns = self._namespaced(key)
        if self._redis_available():
            try:
                raw = self._redis.get(ns)
                self._record_redis_success()
                if raw is not None:
                    self.hits += 1
                    return json.loads(raw)
                self.misses += 1
                return None
            except Exception:
                self._record_redis_failure()
        entry = self._memory.get(ns)
        if entry is None:
            self.misses += 1
            return None
        if (time.monotonic() - entry["at"]) > entry["ttl"]:
            del self._memory[ns]
            self.misses += 1
            return None
        self.hits += 1
        return entry["value"]

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        ns, ttl = self._namespaced(key), ttl or self.default_ttl
        if self._redis_available():
            try:
                self._redis.setex(ns, int(ttl), json.dumps(value, default=str))
                self._record_redis_success()
                return
            except Exception:
                self._record_redis_failure()
        if len(self._memory) > 5000:
            oldest = min(self._memory, key=lambda k: self._memory[k]["at"])
            del self._memory[oldest]
        self._memory[ns] = {"value": value, "at": time.monotonic(), "ttl": ttl}

    def delete(self, key: str) -> None:
        ns = self._namespaced(key)
        if self._redis_available():
            try:
                self._redis.delete(ns)
                self._record_redis_success()
            except Exception:
                self._record_redis_failure()
        self._memory.pop(ns, None)

    def tenant_key(self, tenant_id: str, key: str) -> str:
        return f"t:{tenant_id}:{key}"

    def tenant_get(self, tenant_id: str, key: str) -> Any | None:
        return self.get(self.tenant_key(tenant_id, key))

    def tenant_set(self, tenant_id: str, key: str, value: Any, ttl: float | None = None) -> None:
        self.set(self.tenant_key(tenant_id, key), value, ttl)
