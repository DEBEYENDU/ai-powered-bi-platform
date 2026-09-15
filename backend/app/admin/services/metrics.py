"""Metrics collection with Prometheus exposition.

Dependency note: no prometheus_client required — ``render_prometheus`` emits
the text exposition format from stdlib types, so /metrics works in minimal
environments and scrapes natively where Prometheus is deployed. psutil is used
opportunistically for CPU/memory; otherwise values report as null.

Data sources (all live, no placeholders):
- API latency / throughput / errors: recorded per request by
  ``RequestContextMiddleware`` (see app/middleware/middleware.py).
- DB connections: live SQLAlchemy pool statistics.
- Cache hit rate: live counters aggregated across all CacheService instances.
- Job queue: live Celery inspect; "Not Configured" when no broker is reachable.
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any

LATENCY_BUCKETS_MS = [5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000]


class MetricsCollector:
    def __init__(self, max_series: int = 5000, retention: int = 1000) -> None:
        self._series: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=retention)
        )
        self._max_series = max_series
        self._started_at = time.monotonic()
        self._wall_started_at = time.time()
        # Raw monotonic timestamps of completed requests (throughput window).
        self._request_times: deque[float] = deque(maxlen=20000)
        self._error_count = 0
        self._request_count = 0
        self._lock = threading.Lock()

    # -- recording --
    def record(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        with self._lock:
            if len(self._series) >= self._max_series and name not in self._series:
                oldest = next(iter(self._series))
                del self._series[oldest]
            self._series[name].append(
                {
                    "value": value,
                    "labels": labels or {},
                    "timestamp": (timestamp or datetime.utcnow()).isoformat(),
                }
            )

    def record_request(self, latency_ms: float, status_code: int, route: str = "") -> None:
        """Called once per HTTP request by the middleware."""
        now = time.monotonic()
        with self._lock:
            self._request_times.append(now)
            self._request_count += 1
            labels = {"route": route or "unknown", "status": str(status_code)}
        self.record("api_latency_ms", latency_ms, labels=labels)
        self.record("api_requests_total", 1, labels={"route": labels["route"]})
        if status_code >= 500:
            with self._lock:
                self._error_count += 1
            self.record("api_errors_total", 1, labels={"route": labels["route"]})

    def latest(self, name: str) -> dict[str, Any] | None:
        points = self._series.get(name)
        return points[-1] if points else None

    def query(self, name: str, limit: int = 100) -> list[dict[str, Any]]:
        return list(self._series.get(name, []))[-limit:]

    def series_names(self) -> list[str]:
        return sorted(self._series.keys())

    # -- aggregates --
    def _values(self, name: str) -> list[float]:
        return [float(p["value"]) for p in self._series.get(name, [])]

    def average(self, name: str) -> float:
        values = self._values(name)
        return sum(values) / len(values) if values else 0.0

    def percentile(self, name: str, pct: float) -> float:
        values = sorted(self._values(name))
        if not values:
            return 0.0
        rank = min(len(values) - 1, int(len(values) * pct / 100))
        return values[rank]

    def rate_per_minute(self) -> float:
        """Rolling requests/minute over the last 60 seconds."""
        cutoff = time.monotonic() - 60
        with self._lock:
            return float(sum(1 for t in self._request_times if t >= cutoff))

    def histogram(self, name: str, buckets: list[float] | None = None) -> dict[str, Any]:
        buckets = buckets or LATENCY_BUCKETS_MS
        values = self._values(name)
        counts = [sum(1 for v in values if v <= b) for b in buckets]
        return {
            "buckets": buckets,
            "cumulative_counts": counts,
            "count": len(values),
            "sum": sum(values),
            "inf": len(values),
        }

    # -- live subsystem probes (no placeholders) --
    @staticmethod
    def db_pool_stats() -> dict[str, Any]:
        try:
            from app.db.session import get_engine

            pool = get_engine().pool
            checked_out = 0
            with contextlib.suppress(Exception):
                checked_out = int(pool.checkedout())
            pool_size = 0
            with contextlib.suppress(Exception):
                pool_size = int(pool.size())
            return {
                "open_connections": checked_out,
                "pool_size": pool_size,
                "status": str(pool.status()),
            }
        except Exception as exc:
            return {"open_connections": 0, "pool_size": 0, "error": str(exc)[:200]}

    @staticmethod
    def cache_stats() -> dict[str, Any]:
        try:
            from app.cache.service import CacheService

            return {
                "hit_rate": CacheService.hit_rate(),
                "hits": CacheService.total_hits(),
                "misses": CacheService.total_misses(),
            }
        except Exception as exc:
            return {"hit_rate": 0.0, "hits": 0, "misses": 0, "error": str(exc)[:200]}

    @staticmethod
    def queue_stats() -> dict[str, Any]:
        try:
            from app.admin.services.jobs import JobMonitor

            status = JobMonitor().status()
            if status.get("broker") != "reachable":
                return {"queue_length": "Not Configured", "detail": status.get("detail", "")}
            depth = status.get("reserved", 0) + status.get("scheduled", 0)
            return {"queue_length": depth, "workers": status.get("workers", [])}
        except Exception as exc:
            return {"queue_length": "Not Configured", "error": str(exc)[:200]}

    # -- snapshots --
    def system_snapshot(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {"uptime_seconds": round(time.time() - self._wall_started_at, 1)}
        try:
            import psutil  # type: ignore

            from app.core.config import get_settings

            try:
                disk_path = get_settings().storage_path
            except Exception:
                disk_path = "/"
            snapshot.update(
                {
                    "cpu_percent": psutil.cpu_percent(interval=0.1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": psutil.disk_usage(disk_path).percent,
                }
            )
        except Exception:
            snapshot.update({"cpu_percent": None, "memory_percent": None, "disk_percent": None})
        pool = self.db_pool_stats()
        cache = self.cache_stats()
        queue = self.queue_stats()
        snapshot.update(
            {
                "api_latency_ms": round(self.average("api_latency_ms"), 2),
                "api_latency_p95_ms": round(self.percentile("api_latency_ms", 95), 2),
                "avg_response_time_ms": round(self.average("api_latency_ms"), 2),
                "api_throughput_rpm": self.rate_per_minute(),
                "api_requests_total": self._request_count,
                "api_errors_total": self._error_count,
                "cache_hit_rate": cache["hit_rate"],
                "cache_hits": cache["hits"],
                "cache_misses": cache["misses"],
                "db_connections": pool["open_connections"],
                "db_pool": {k: v for k, v in pool.items() if k != "open_connections"},
                "job_queue_length": queue["queue_length"],
            }
        )
        return snapshot

    def platform_snapshot(self) -> dict[str, Any]:
        """Cross-module status reusing existing services (no duplicated logic)."""
        snapshot: dict[str, Any] = {}
        try:
            from app.ai.monitoring.observability import AIMonitor  # type: ignore

            snapshot["ai"] = AIMonitor().get_dashboard()
        except Exception as exc:
            snapshot["ai"] = {"error": str(exc)[:200]}
        try:
            from app.ai.tools.registry import ToolRegistry  # type: ignore

            snapshot["ai_tools"] = len(ToolRegistry().list_tools())
        except Exception as exc:
            snapshot["ai_tools"] = str(exc)[:200]
        try:
            from app.reports.exporters.exporters import SUPPORTED_FORMATS  # type: ignore

            snapshot["report_formats"] = SUPPORTED_FORMATS
        except Exception as exc:
            snapshot["report_formats"] = str(exc)[:200]
        return snapshot

    # -- prometheus exposition --
    def render_prometheus(self) -> str:
        lines = ["# BI platform metrics"]
        for name in sorted(self._series):
            points = self._series[name]
            if not points:
                continue
            safe = "bi_" + "".join(c if c.isalnum() else "_" for c in name)
            if name.endswith("_total"):
                lines.append(f"# TYPE {safe} counter")
            else:
                lines.append(f"# TYPE {safe} gauge")
            by_labels: dict[str, dict[str, Any]] = {}
            for p in points:
                key = ",".join(f"{k}={v}" for k, v in sorted(p["labels"].items()))
                by_labels[key] = p  # last wins per label set
            for p in by_labels.values():
                label_str = (
                    "{" + ",".join(f'{k}="{v}"' for k, v in sorted(p["labels"].items())) + "}"
                    if p["labels"]
                    else ""
                )
                lines.append(f"{safe}{label_str} {p['value']}")
        # Request-duration histogram (computed from retained latency points).
        hist = self.histogram("api_latency_ms")
        lines.append("# TYPE bi_request_duration_ms histogram")
        for bound, cumulative in zip(hist["buckets"], hist["cumulative_counts"], strict=True):
            lines.append(f'bi_request_duration_ms_bucket{{le="{bound}"}} {cumulative}')
        lines.append(f'bi_request_duration_ms_bucket{{le="+Inf"}} {hist["inf"]}')
        lines.append(f"bi_request_duration_ms_sum {hist['sum']}")
        lines.append(f"bi_request_duration_ms_count {hist['count']}")
        # Live gauges.
        pool = self.db_pool_stats()
        lines.append("# TYPE bi_db_open_connections gauge")
        lines.append(f"bi_db_open_connections {pool['open_connections']}")
        cache = self.cache_stats()
        lines.append("# TYPE bi_cache_hit_rate gauge")
        lines.append(f"bi_cache_hit_rate {cache['hit_rate']}")
        queue = self.queue_stats()
        if isinstance(queue["queue_length"], (int, float)):
            lines.append("# TYPE bi_job_queue_length gauge")
            lines.append(f"bi_job_queue_length {queue['queue_length']}")
        return "\n".join(lines) + "\n"
