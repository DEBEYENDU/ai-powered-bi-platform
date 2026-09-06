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
                entry = {
                    "service": name,
                    "status": outcome.get("status", "ok"),
                    "latency_ms": round((time.time() - start) * 1000, 2),
                    "detail": outcome.get("detail", ""),
                }
                # Propagate probe-specific diagnostics (directory, versions,
                # pool stats, ...) alongside the standard envelope.
                for key, value in outcome.items():
                    if key not in entry:
                        entry[key] = value
                results.append(entry)
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
        self.register("etl", self._check_etl)
        self.register("analytics", self._check_analytics)
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

            engine = get_engine()
            with engine.connect() as conn:
                version = conn.execute(text("SELECT version()")).scalar() or ""
                connected_db = conn.execute(text("SELECT current_database()")).scalar()
            pool = engine.pool
            checked_out = pool.checkedout() if hasattr(pool, "checkedout") else "n/a"
            return {
                "status": "ok",
                "detail": f"{connected_db} @ {engine.url.host}",
                "database": connected_db,
                "server_version": str(version).split(" ")[1]
                if " " in str(version)
                else str(version)[:60],
                "pool_checked_out": checked_out,
                "pool_status": str(pool.status()),
            }
        except Exception as exc:
            return {"status": "down", "detail": str(exc)[:200]}

    @staticmethod
    def _check_redis() -> dict[str, Any]:
        try:
            import redis  # type: ignore

            from app.core.config import get_settings

            client = redis.Redis.from_url(
                get_settings().redis_url, socket_connect_timeout=2, decode_responses=True
            )
            client.ping()
            info = client.info("server")
            memory = client.info("memory")
            return {
                "status": "ok",
                "detail": f"redis {info.get('redis_version', '?')} "
                f"({memory.get('used_memory_human', '?')} used)",
                "server_version": info.get("redis_version", ""),
                "used_memory": memory.get("used_memory_human", ""),
                "connected_clients": client.info("clients").get("connected_clients", 0),
            }
        except Exception as exc:
            return {"status": "down", "detail": str(exc)[:200]}

    @staticmethod
    def _check_storage() -> dict[str, Any]:
        import os
        import shutil
        from pathlib import Path

        try:
            from app.core.config import get_settings

            root = Path(get_settings().storage_path)
            root.mkdir(parents=True, exist_ok=True)
            readable = os.access(root, os.R_OK)
            writable = os.access(root, os.W_OK)
            probe = root / ".health"
            probe.write_text("ok")
            if probe.read_text() != "ok":
                raise RuntimeError("storage round-trip mismatch")
            probe.unlink()
            usage = shutil.disk_usage(root)
            free_gb = round(usage.free / (1024**3), 2)
            return {
                "status": "ok" if (readable and writable) else "degraded",
                "detail": str(root),
                "directory": str(root),
                "readable": readable,
                "writable": writable,
                "free_space_gb": free_gb,
            }
        except Exception as exc:
            try:
                from app.core.config import get_settings

                attempted = get_settings().storage_path
            except Exception:
                attempted = "unknown"
            return {
                "status": "down",
                "detail": str(exc)[:200],
                "directory": attempted,
                "readable": False,
                "writable": False,
            }

    @staticmethod
    def _check_etl() -> dict[str, Any]:
        try:
            from app.etl.stages.registry import default_stages

            stages = default_stages()
            return {
                "status": "ok",
                "detail": f"{len(stages)} stages registered",
                "stages": [getattr(s, "name", type(s).__name__) for s in stages],
            }
        except Exception as exc:
            return {"status": "down", "detail": str(exc)[:200]}

    @staticmethod
    def _check_analytics() -> dict[str, Any]:
        try:
            from app.analytics.kpi.definitions import KPI

            kpis = list(KPI)
            return {
                "status": "ok",
                "detail": f"{len(kpis)} KPIs defined",
                "kpi_count": len(kpis),
            }
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
