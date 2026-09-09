"""HealthMonitor + StatusMonitor: poll the backend, aggregate status.

HealthMonitor fetches /health, /api/v1/admin/health and maintenance mode on
an interval in a background thread and notifies subscribers. StatusMonitor
merges process state + dependency checks into the red/yellow/green panel.
"""

from __future__ import annotations

import contextlib
import threading
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from launcher import checks
from launcher.logs import LogStore
from launcher.paths import ProjectPaths

STATUS_RUNNING = "running"
STATUS_STARTING = "starting"
STATUS_STOPPED = "stopped"
STATUS_WARNING = "warning"


@dataclass
class ServiceStatus:
    name: str
    status: str = STATUS_STOPPED
    detail: str = ""


def _fetch_json(url: str, timeout: float = 5.0) -> Any | None:
    try:
        # only localhost backend URLs are ever fetched here.
        with urllib.request.urlopen(url, timeout=timeout) as response:
            import json

            return json.loads(response.read().decode("utf-8", "replace"))
    except (OSError, ValueError):
        # URLError is an OSError; malformed bodies are ValueErrors.
        # Unreachable backend is routine (project stopped) — not an error.
        return None


class HealthMonitor:
    def __init__(
        self,
        backend_port: int,
        logs: LogStore,
        interval: float = 5.0,
        on_update: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.backend_port = backend_port
        self.logs = logs
        self.interval = interval
        self.on_update = on_update
        self.snapshot: dict[str, Any] = {}
        self.last_response_ms: float = 0.0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.backend_port}"

    def poll_once(self) -> dict[str, Any]:
        started = time.time()
        api = _fetch_json(f"{self.base}/health")
        elapsed_ms = round((time.time() - started) * 1000, 1)
        self.last_response_ms = elapsed_ms
        # The aggregate probe runs live DB/dependency checks; allow longer.
        admin_health = _fetch_json(f"{self.base}/api/v1/admin/health", timeout=30.0) or {}
        maintenance = _fetch_json(f"{self.base}/api/v1/admin/maintenance") or {}
        self.snapshot = {
            "api": api or {},
            "services": admin_health.get("services", []),
            "overall": admin_health.get("overall", "unknown"),
            "maintenance": maintenance.get("mode", "unknown"),
            "response_ms": elapsed_ms,
            "reachable": api is not None,
        }
        if self.on_update:
            with contextlib.suppress(Exception):
                self.on_update(self.snapshot)
        return self.snapshot

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _loop(self) -> None:
        while not self._stop_event.wait(self.interval):
            try:
                self.poll_once()
            except Exception as exc:  # noqa: BLE001
                self.logs.append("launcher", f"Health poll failed: {exc}")


class StatusMonitor:
    """Aggregate red/yellow/green status for the status panel."""

    def __init__(self, paths: ProjectPaths) -> None:
        self.paths = paths

    def collect(
        self,
        backend_running: bool,
        frontend_running: bool,
        backend_starting: bool = False,
        frontend_starting: bool = False,
        health_snapshot: dict[str, Any] | None = None,
    ) -> list[ServiceStatus]:
        db = checks.check_postgres()
        redis = checks.check_redis()
        storage_ok = self.paths.root.is_dir()
        items = [
            ServiceStatus(
                "Backend",
                STATUS_RUNNING
                if backend_running
                else (STATUS_STARTING if backend_starting else STATUS_STOPPED),
            ),
            ServiceStatus(
                "Frontend",
                STATUS_RUNNING
                if frontend_running
                else (STATUS_STARTING if frontend_starting else STATUS_STOPPED),
            ),
            ServiceStatus("Database", STATUS_RUNNING if db.ok else STATUS_STOPPED, db.message),
            ServiceStatus("Redis", STATUS_RUNNING if redis.ok else STATUS_WARNING, redis.message),
            ServiceStatus("Storage", STATUS_RUNNING if storage_ok else STATUS_STOPPED),
        ]
        if health_snapshot:
            overall = str(health_snapshot.get("overall", "unknown"))
            items.append(
                ServiceStatus(
                    "Health",
                    STATUS_RUNNING
                    if overall == "ok"
                    else (STATUS_WARNING if overall == "degraded" else STATUS_STOPPED),
                    f"overall={overall}",
                )
            )
            items.append(
                ServiceStatus(
                    "Maintenance",
                    STATUS_RUNNING,
                    f"mode={health_snapshot.get('maintenance', '?')}",
                )
            )
        else:
            items.append(ServiceStatus("Health", STATUS_STOPPED, "backend unreachable"))
            items.append(ServiceStatus("Maintenance", STATUS_STOPPED, "unknown"))
        return items

    @staticmethod
    def system_stats() -> dict[str, float]:
        stats = {"cpu": 0.0, "memory": 0.0, "disk": 0.0}
        with contextlib.suppress(Exception):
            import psutil

            stats["cpu"] = float(psutil.cpu_percent(interval=0.2))
            stats["memory"] = float(psutil.virtual_memory().percent)
            stats["disk"] = float(psutil.disk_usage(Path.cwd().anchor).percent)
        return stats
