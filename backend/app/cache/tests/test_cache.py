"""Tests for CacheService (Redis + in-memory fallback) and analytics cache."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from app.cache.service import _COOLDOWN_SECS, _FAIL_THRESHOLD, CacheService


@pytest.fixture(autouse=True)
def _no_real_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent CacheService from trying to connect to real Redis."""
    monkeypatch.setattr(
        "app.cache.service.CacheService._init_redis", lambda self: None
    )


# ---------------------------------------------------------------------------
# CacheService — in-memory fallback (no Redis)
# ---------------------------------------------------------------------------


class TestCacheServiceMemory:
    """When Redis is unavailable, CacheService should fall back to memory."""

    def test_set_get_roundtrip(self) -> None:
        svc = CacheService(namespace="test_mem_rt")
        svc.set("key1", {"a": 1}, ttl=60)
        assert svc.get("key1") == {"a": 1}

    def test_get_missing_returns_none(self) -> None:
        svc = CacheService(namespace="test_mem_miss")
        assert svc.get("nonexistent") is None

    def test_ttl_expiry(self) -> None:
        svc = CacheService(namespace="test_mem_ttl")
        svc.set("short", "val", ttl=0.01)
        time.sleep(0.05)
        assert svc.get("short") is None

    def test_delete_removes_key(self) -> None:
        svc = CacheService(namespace="test_mem_del")
        svc.set("k", "v", ttl=60)
        svc.delete("k")
        assert svc.get("k") is None

    def test_hit_miss_counters(self) -> None:
        svc = CacheService(namespace="test_mem_counters")
        svc.set("x", 1, ttl=60)
        svc.get("x")  # hit
        svc.get("y")  # miss
        assert svc.hits == 1
        assert svc.misses == 1

    def test_memory_eviction_at_5000(self) -> None:
        svc = CacheService(namespace="test_mem_evict")
        for i in range(5001):
            svc.set(f"k{i}", i, ttl=3600)
        # Should not crash; at most 5000 entries + the new one
        assert len(svc._memory) <= 5001


# ---------------------------------------------------------------------------
# CacheService — circuit breaker
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    """Verify the circuit breaker trips after consecutive failures and recovers."""

    def test_circuit_opens_after_failures(self) -> None:
        svc = CacheService(namespace="test_circuit")
        # Force a mock Redis that always fails
        mock_redis = MagicMock()
        mock_redis.get.side_effect = ConnectionError("down")
        svc._redis = mock_redis

        for _ in range(_FAIL_THRESHOLD):
            svc.get("k")

        # Circuit should be open — Redis calls should be skipped
        assert svc._redis_available() is False
        mock_redis.get.assert_called()  # called during failure window

    def test_circuit_closes_after_cooldown(self) -> None:
        svc = CacheService(namespace="test_circuit_cooldown")
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        svc._redis = mock_redis
        svc._consecutive_failures = _FAIL_THRESHOLD
        svc._circuit_open_at = time.monotonic() - _COOLDOWN_SECS - 1

        # After cooldown, circuit should close
        assert svc._redis_available() is True

    def test_success_resets_failure_count(self) -> None:
        svc = CacheService(namespace="test_circuit_reset")
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        svc._redis = mock_redis
        svc._consecutive_failures = 3

        svc.get("k")  # succeeds
        assert svc._consecutive_failures == 0


# ---------------------------------------------------------------------------
# CacheService — hit_rate aggregation
# ---------------------------------------------------------------------------


class TestHitRate:
    def test_hit_rate_across_instances(self) -> None:
        s1 = CacheService(namespace="test_rate_1")
        s2 = CacheService(namespace="test_rate_2")
        s1.set("a", 1, ttl=60)
        s2.set("b", 2, ttl=60)
        s1.get("a")  # hit
        s2.get("b")  # hit
        s2.get("c")  # miss
        rate = CacheService.hit_rate()
        assert 0.0 <= rate <= 1.0
        assert CacheService.total_hits() >= 2


# ---------------------------------------------------------------------------
# Analytics cache — fallback
# ---------------------------------------------------------------------------


class TestAnalyticsCache:
    """analytics/cache.py should fall back to memory when Redis is down."""

    def test_cache_set_get_without_redis(self) -> None:
        import app.analytics.cache as ac

        # Force Redis to be unavailable
        with patch.object(ac, "_pool", None), patch.object(ac, "_pool_healthy", False):
            ac.cache_set("analytics_key", "analytics_val", ttl=60)
            result = ac.cache_get("analytics_key")
            assert result == "analytics_val"

    def test_cache_get_expired_returns_none(self) -> None:
        import app.analytics.cache as ac

        with patch.object(ac, "_pool", None), patch.object(ac, "_pool_healthy", False):
            ac.cache_set("exp_key", "val", ttl=0)
            # Manually set expiry in the past
            ac._memory["exp_key"] = ("val", time.monotonic() - 1)
            assert ac.cache_get("exp_key") is None

    def test_cache_get_missing_returns_none(self) -> None:
        import app.analytics.cache as ac

        with patch.object(ac, "_pool", None), patch.object(ac, "_pool_healthy", False):
            assert ac.cache_get("nonexistent_analytics") is None
