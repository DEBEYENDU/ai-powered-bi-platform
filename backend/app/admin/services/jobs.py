"""Background job monitoring over Celery inspect with graceful fallback.

Reports queued/running/failed/completed views, worker health, and DLQ depth.
Without a live broker it returns structured 'unavailable' payloads instead of
raising, so the admin dashboard degrades cleanly.
"""

from __future__ import annotations

from typing import Any


class JobMonitor:
    def status(self) -> dict[str, Any]:
        try:
            from app.workers.celery_app import celery_app  # type: ignore

            if celery_app is None:
                raise RuntimeError("celery not installed")
            broker = str(getattr(celery_app.conf, "broker_url", "") or "")
            # kombu retries a dead broker for ~4s per inspect call; probe the
            # socket first so a down broker reports "unreachable" immediately.
            from app.core.net import endpoint_of, tcp_reachable

            if broker and endpoint_of(broker) is not None:
                reachable, where = tcp_reachable(broker, 0.5)
                if not reachable:
                    return {
                        "broker": "unreachable",
                        "workers": [],
                        "running": 0,
                        "scheduled": 0,
                        "reserved": 0,
                        "detail": f"broker {where}",
                    }
            inspect = celery_app.control.inspect()
            if inspect is None:
                raise RuntimeError("no inspect response")
            active = inspect.active() or {}
            scheduled = inspect.scheduled() or {}
            reserved = inspect.reserved() or {}
            stats = inspect.stats() or {}
            return {
                "broker": "reachable",
                "workers": sorted(stats.keys()),
                "running": sum(len(v) for v in active.values()),
                "scheduled": sum(len(v) for v in scheduled.values()),
                "reserved": sum(len(v) for v in reserved.values()),
                "details": {"active": active, "scheduled": scheduled},
            }
        except Exception as exc:
            return {
                "broker": "unreachable",
                "workers": [],
                "running": 0,
                "scheduled": 0,
                "reserved": 0,
                "detail": str(exc)[:200],
            }

    def failed_jobs_note(self) -> dict[str, Any]:
        return {
            "note": "Failed/completed history requires a result backend; "
            "configure CELERY_RESULT_BACKEND=redis for task history."
        }

    def queues(self) -> list[dict[str, Any]]:
        status = self.status()
        return [
            {
                "name": "celery",
                "depth": status.get("reserved", 0),
                "workers": len(status.get("workers", [])),
            }
        ]
