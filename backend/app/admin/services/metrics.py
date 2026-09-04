"""Metrics collection with Prometheus exposition.

Dependency note: no prometheus_client required — ``render_prometheus`` emits
the text exposition format from stdlib types, so /metrics works in minimal
environments and scrapes natively where Prometheus is deployed. psutil is used
opportunistically for CPU/memory; otherwise values report as null/0.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any


class MetricsCollector:
    def __init__(self, max_series: int = 5000, retention: int = 1000) -> None:
        self._series: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=retention)
        )
        self._max_series = max_series
        self._started_at = time.time()

    def record(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
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

    def latest(self, name: str) -> dict[str, Any] | None:
        points = self._series.get(name)
        return points[-1] if points else None

    def query(self, name: str, limit: int = 100) -> list[dict[str, Any]]:
        return list(self._series.get(name, []))[-limit:]

    def series_names(self) -> list[str]:
        return sorted(self._series.keys())

    def render_prometheus(self) -> str:
        lines = ["# BI platform metrics"]
        for name in sorted(self._series):
            points = self._series[name]
            if not points:
                continue
            safe = "bi_" + "".join(c if c.isalnum() else "_" for c in name)
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
        return "\n".join(lines) + "\n"

    def system_snapshot(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {"uptime_seconds": round(time.time() - self._started_at, 1)}
        try:
            import psutil  # type: ignore

            snapshot.update(
                {
                    "cpu_percent": psutil.cpu_percent(interval=0.1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": psutil.disk_usage("/").percent,
                }
            )
        except Exception:
            snapshot.update({"cpu_percent": None, "memory_percent": None, "disk_percent": None})
        for name in (
            "api_latency_ms",
            "api_throughput_rpm",
            "cache_hit_rate",
            "db_connections",
            "job_queue_length",
        ):
            latest = self.latest(name)
            snapshot[name] = latest["value"] if latest else 0
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
