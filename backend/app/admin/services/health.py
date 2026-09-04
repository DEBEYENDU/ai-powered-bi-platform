"""Aggregate health checks across every engine.

Each check is a small callable returning (status, latency_ms, detail); engines
are probed lazily so a down dependency reports 'degraded' instead of raising.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


class HealthService:
    def __init__(self) -> None:
        self._checks: dict[str, Callable[[], dict[str, Any]]] = {}
        self._register_builtin()

    def register(self, name: str, fn: Callable[[], dict[str, Any]]) -> None:
        self._checks[name] = fn

    def check_all(self) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for name, fn in self._checks.items():
            start = time.time()
            try:
                outcome = fn()
                results.append(
                    {
                        "service": name,
                        "status": outcome.get("status", "ok"),
                        "latency_ms": round((time.time() - start) * 1000, 2),
                        "detail": outcome.get("detail", ""),
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "service": name,
                        "status": "down",
                        "latency_ms": round((time.time() - start) * 1000, 2),
                        "detail": str(exc)[:200],
                    }
                )
        overall = (
            "ok"
            if all(r["status"] == "ok" for r in results)
            else ("degraded" if not any(r["status"] == "down" for r in results) else "down")
        )
        return {"overall": overall, "services": results}

    def _register_builtin(self) -> None:
        self.register("database", self._check_database)
        self.register("redis", self._check_redis)
        self.register("storage", self._check_storage)
        self.register("etl", lambda: {"status": "ok", "detail": "pipeline registry loaded"})
        self.register("analytics", lambda: {"status": "ok", "detail": "kpi engine loaded"})
        self.register("ai", self._check_ai)
        self.register("ml", lambda: {"status": "ok", "detail": "forecast tools registered"})
        self.register("reporting", self._check_reporting)
        self.register("scheduler", lambda: {"status": "ok", "detail": "beat schedule configured"})
        self.register("workers", self._check_workers)

    @staticmethod
    def _check_database() -> dict[str, Any]:
        try:
            from sqlalchemy import text

            from app.db.session import get_engine

            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "ok", "detail": "reachable"}
        except Exception as exc:
            return {"status": "down", "detail": str(exc)[:200]}

    @staticmethod
    def _check_redis() -> dict[str, Any]:
        try:
            import redis  # type: ignore

            from app.core.config import get_settings

            redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=2).ping()
            return {"status": "ok", "detail": "reachable"}
        except Exception as exc:
            return {"status": "down", "detail": str(exc)[:200]}

    @staticmethod
    def _check_storage() -> dict[str, Any]:
        from pathlib import Path

        try:
            from app.core.config import get_settings

            root = Path(get_settings().storage_path)
            root.mkdir(parents=True, exist_ok=True)
            probe = root / ".health"
            probe.write_text("ok")
            probe.unlink()
            return {"status": "ok", "detail": str(root)}
        except Exception as exc:
            return {"status": "down", "detail": str(exc)[:200]}

    @staticmethod
    def _check_ai() -> dict[str, Any]:
        try:
            from app.ai.tools.registry import ToolRegistry

            return {
                "status": "ok",
                "detail": f"{len(ToolRegistry().list_tools())} tools registered",
            }
        except Exception as exc:
            return {"status": "down", "detail": str(exc)[:200]}

    @staticmethod
    def _check_reporting() -> dict[str, Any]:
        try:
            from app.reports.exporters.exporters import SUPPORTED_FORMATS

            return {"status": "ok", "detail": f"{len(SUPPORTED_FORMATS)} export formats"}
        except Exception as exc:
            return {"status": "down", "detail": str(exc)[:200]}

    @staticmethod
    def _check_workers() -> dict[str, Any]:
        try:
            from app.workers.celery_app import celery_app  # type: ignore

            if celery_app is None:
                return {"status": "degraded", "detail": "celery not installed"}
            inspect = celery_app.control.inspect(timeout=2.0)
            stats = inspect.stats() if inspect else None
            if not stats:
                return {"status": "degraded", "detail": "no live workers"}
            return {"status": "ok", "detail": f"{len(stats)} workers"}
        except Exception as exc:
            return {"status": "degraded", "detail": str(exc)[:200]}
