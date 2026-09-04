"""Celery application for background tasks (ETL jobs, report generation).

Broker/backend default to Redis; tasks are also import-safe without a broker
because job modules degrade to synchronous execution.
"""

from __future__ import annotations

from app.core.config import get_settings

try:
    from celery import Celery  # type: ignore

    settings = get_settings()
    celery_app = Celery(
        "bi_platform",
        broker=settings.redis_url,
        backend=settings.redis_url,
    )
    celery_app.conf.update(
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_default_retry_delay=60,
        beat_schedule={
            # Report schedules are polled; Scheduler.due_schedules() decides work.
            "reports-run-due-schedules": {
                "task": "reports.run_due_schedules",
                "schedule": 300.0,
            },
        },
    )

    # Ensure task modules register.
    import app.reports.jobs.tasks  # noqa: F401
except ImportError:  # pragma: no cover - celery optional in minimal envs
    celery_app = None  # type: ignore[assignment]
