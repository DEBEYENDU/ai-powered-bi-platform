"""Background jobs for reports (Celery-compatible signatures).

Each task degrades to synchronous execution when Celery is unavailable, so
scheduling/distribution logic stays testable without a broker.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from celery import shared_task  # type: ignore

    def _task(*dargs: Any, **dkwargs: Any):  # type: ignore
        return shared_task(*dargs, **dkwargs)
    HAS_CELERY = True
except Exception:
    HAS_CELERY = False

    def _task(*dargs: Any, **dkwargs: Any):  # type: ignore
        def wrap(fn):  # type: ignore
            fn.delay = fn  # type: ignore
            return fn
        return wrap


@_task(name="reports.generate", bind=True, max_retries=3)
def generate_report_task(self: Any, report_id: str, formats: Optional[List[str]] = None,
                         variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    import asyncio
    from app.reports.services.report_service import ReportService

    service = ReportService()
    try:
        return asyncio.run(service.generate(report_id=report_id, formats=formats or ["pdf"],
                                            variables=variables or {}))
    except Exception as exc:
        if HAS_CELERY and hasattr(self, "retry"):
            raise self.retry(exc=exc, countdown=60)
        return {"report_id": report_id, "status": "failed", "error": str(exc)}


@_task(name="reports.run_due_schedules")
def run_due_schedules_task() -> Dict[str, Any]:
    from app.reports.services.report_service import ReportService

    service = ReportService()
    due = service.scheduler.due_schedules()
    results = []
    for sched in due:
        try:
            import asyncio
            result = asyncio.run(service.generate(
                report_id=sched.report_id, formats=["pdf"],
                variables={}, user_id="scheduler"))
            service.scheduler.record_run(sched.schedule_id, True)
            service.distribution.deliver_email(
                sched.report_id, result.get("artifacts", []),
                sched.distribution.get("recipients", []))
            service.events.publish("report_delivered", sched.report_id, "scheduler",
                                   details={"schedule_id": sched.schedule_id})
            results.append({"schedule_id": sched.schedule_id, "status": "ok"})
        except Exception as exc:
            service.scheduler.record_run(sched.schedule_id, False)
            service.events.publish("report_failed", sched.report_id, "scheduler",
                                   details={"error": str(exc)})
            results.append({"schedule_id": sched.schedule_id, "status": "failed"})
    return {"processed": len(results), "results": results}
