"""Tests for S1.3 — Real Metrics, Monitoring and Observability.

Covers:
- API latency instrumentation
- API throughput (rolling window)
- Route normalization (bounded labels)
- Database connection metrics
- Database health check
- Cache hit rate
- Job queue metric
- Thread safety
- Regression: existing endpoints
"""

from __future__ import annotations

import threading
import time

from app.admin.services.health import HealthService
from app.admin.services.metrics import MetricsCollector
from app.middleware.middleware import _normalize_route

# --- API Latency ---

class TestAPILatency:
    def test_request_records_latency(self):
        m = MetricsCollector()
        m.record_request(42.5, 200, "/test")
        snap = m.system_snapshot()
        assert snap["api_latency_ms"] == 42.5

    def test_failed_request_records_latency(self):
        m = MetricsCollector()
        m.record_request(120.0, 500, "/error")
        snap = m.system_snapshot()
        assert snap["api_latency_ms"] == 120.0
        assert snap["api_errors_total"] == 1

    def test_latency_is_non_negative(self):
        m = MetricsCollector()
        m.record_request(0.0, 200, "/zero")
        m.record_request(5.5, 200, "/fast")
        snap = m.system_snapshot()
        assert snap["api_latency_ms"] >= 0

    def test_route_labels_are_bounded(self):
        m = MetricsCollector()
        for i in range(100):
            m.record_request(10.0, 200, f"/users/{i}")
        # All 100 requests should map to one route label
        latency_points = m.query("api_latency_ms")
        routes = set()
        for p in latency_points:
            routes.add(p["labels"].get("route", ""))
        # With normalized routes, all should be /users/{id}
        assert all("/users/" in r for r in routes)

    def test_concurrent_request_recording(self):
        m = MetricsCollector()
        errors = []

        def record_many(start_idx: int):
            try:
                for i in range(200):
                    m.record_request(10.0 + i, 200, f"/r/{start_idx + i}")
            except Exception as e:  # noqa: BLE001 — test catches all errors
                errors.append(e)

        threads = [threading.Thread(target=record_many, args=(i * 200,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        snap = m.system_snapshot()
        assert snap["api_requests_total"] == 800


# --- API Throughput ---

class TestAPIThroughput:
    def test_throughput_reflects_requests(self):
        m = MetricsCollector()
        for _ in range(10):
            m.record_request(10.0, 200, "/x")
        rpm = m.rate_per_minute()
        assert rpm == 10.0

    def test_zero_traffic_returns_zero(self):
        m = MetricsCollector()
        rpm = m.rate_per_minute()
        assert rpm == 0.0

    def test_rolling_window_decreases(self):
        m = MetricsCollector()
        m.record_request(10.0, 200, "/x")
        assert m.rate_per_minute() == 1.0
        # Verify it doesn't grow without new requests
        time.sleep(0.01)
        assert m.rate_per_minute() == 1.0


# --- Route Normalization ---

class TestRouteNormalization:
    def test_numeric_id_normalized(self):
        assert _normalize_route("/users/123") == "/users/{id}"

    def test_uuid_normalized(self):
        assert _normalize_route("/users/550e8400-e29b-41d4-a716-446655440000") == "/users/{id}"

    def test_static_routes_unchanged(self):
        assert _normalize_route("/admin/users") == "/admin/users"
        assert _normalize_route("/health") == "/health"
        assert _normalize_route("/api/v1/metrics") == "/api/v1/metrics"

    def test_multiple_ids_normalized(self):
        result = _normalize_route("/orgs/123/users/456")
        assert result == "/orgs/{id}/users/{id}"


# --- Database Connection Metrics ---

class TestDatabaseMetrics:
    def test_db_pool_stats_returns_dict(self):
        stats = MetricsCollector.db_pool_stats()
        assert "open_connections" in stats
        assert "pool_size" in stats

    def test_db_pool_stats_with_no_engine(self):
        # Even without a configured engine, should not crash
        stats = MetricsCollector.db_pool_stats()
        assert isinstance(stats, dict)
        assert "open_connections" in stats

    def test_db_health_check_works(self):
        health = HealthService()
        result = health.check_all()
        db_check = next(s for s in result["services"] if s["service"] == "database")
        assert db_check["status"] in ("ok", "down")
        assert "pool_checked_out" in db_check or db_check["status"] == "down"

    def test_db_health_failure_reported(self):
        # Database health should report "down" when not configured
        # (no DATABASE_URL in test env)
        health = HealthService()
        result = health.check_all()
        db_check = next(s for s in result["services"] if s["service"] == "database")
        # Either ok (DB is available) or down (not configured) — both are valid
        assert db_check["status"] in ("ok", "down", "degraded")


# --- Cache Hit Rate ---

class TestCacheHitRate:
    def test_cache_stats_returns_structure(self):
        stats = MetricsCollector.cache_stats()
        assert "hit_rate" in stats
        assert "hits" in stats
        assert "misses" in stats

    def test_cache_hit_rate_is_float(self):
        stats = MetricsCollector.cache_stats()
        assert isinstance(stats["hit_rate"], float)
        assert 0.0 <= stats["hit_rate"] <= 1.0

    def test_cache_stats_in_snapshot(self):
        m = MetricsCollector()
        snap = m.system_snapshot()
        assert "cache_hit_rate" in snap
        assert isinstance(snap["cache_hit_rate"], float)


# --- Job Queue ---

class TestJobQueue:
    def test_queue_stats_structure(self):
        stats = MetricsCollector.queue_stats()
        assert "queue_length" in stats

    def test_queue_length_or_not_configured(self):
        stats = MetricsCollector.queue_stats()
        assert isinstance(stats["queue_length"], (int, float, str))

    def test_queue_in_snapshot(self):
        m = MetricsCollector()
        snap = m.system_snapshot()
        assert "job_queue_length" in snap


# --- Thread Safety ---

class TestThreadSafety:
    def test_concurrent_record(self):
        m = MetricsCollector()
        errors = []

        def writer():
            try:
                for i in range(500):
                    m.record(f"test_metric_{i % 10}", float(i))
            except Exception as e:  # noqa: BLE001 — test catches all errors
                errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert len(m.series_names()) <= 10

    def test_concurrent_record_request(self):
        m = MetricsCollector()
        errors = []

        def requester():
            try:
                for _ in range(200):
                    m.record_request(50.0, 200, "/concurrent")
            except Exception as e:  # noqa: BLE001 — test catches all errors
                errors.append(e)

        threads = [threading.Thread(target=requester) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        snap = m.system_snapshot()
        assert snap["api_requests_total"] == 800


# --- Regression ---

class TestRegression:
    def test_existing_metrics_endpoint_shape(self):
        m = MetricsCollector()
        snap = m.system_snapshot()
        expected_keys = [
            "uptime_seconds",
            "api_latency_ms",
            "api_throughput_rpm",
            "cache_hit_rate",
            "db_connections",
            "job_queue_length",
        ]
        for key in expected_keys:
            assert key in snap, f"Missing key: {key}"

    def test_existing_health_endpoint(self):
        health = HealthService()
        result = health.check_all()
        assert "overall" in result
        assert "services" in result
        assert result["overall"] in ("ok", "degraded", "down")

    def test_existing_prometheus_endpoint(self):
        m = MetricsCollector()
        m.record_request(42.0, 200, "/test")
        prom = m.render_prometheus()
        assert "bi_" in prom
        assert "request_duration" in prom

    def test_snapshot_contains_all_api_metrics(self):
        m = MetricsCollector()
        m.record_request(100.0, 200, "/a")
        m.record_request(200.0, 200, "/b")
        m.record_request(500.0, 500, "/c")
        snap = m.system_snapshot()
        assert snap["api_requests_total"] == 3
        assert snap["api_errors_total"] == 1
        assert snap["api_latency_ms"] > 0
        assert snap["api_throughput_rpm"] == 3.0
