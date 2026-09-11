"""Workflow scheduler — manages cron/scheduled workflow execution."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from app.core.logging import get_logger
from app.workflows.schemas import TriggerType
from app.workflows.triggers.handler import compute_next_run

log = get_logger("workflow.scheduler")


class WorkflowScheduler:
    """Polls active workflows and triggers them when their schedule is due.

    Uses Celery beat when available, otherwise runs an in-process polling loop.
    """

    def __init__(self) -> None:
        self._running = False
        self._poll_interval = 60  # seconds

    async def start(self) -> None:
        """Start the scheduler polling loop."""
        if self._running:
            return
        self._running = True
        log.info("scheduler_started")
        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                log.error("scheduler_tick_error", error=str(exc))
            await asyncio.sleep(self._poll_interval)

    def stop(self) -> None:
        self._running = False
        log.info("scheduler_stopped")

    async def _tick(self) -> None:
        """Check all active workflows and run any that are due."""
        from app.db.session import get_db_session
        from app.workflows.models import WorkflowRecord

        with get_db_session() as db:
            if db is None:
                return
            workflows = (
                db.query(WorkflowRecord)
                .filter(
                    WorkflowRecord.status == "active",
                    WorkflowRecord.deleted_at.is_(None),
                )
                .all()
            )

            for wf in workflows:
                trigger_config = wf.trigger_config or {}
                trigger_type = trigger_config.get("type", "manual")
                if trigger_type == TriggerType.MANUAL:
                    continue

                last_run = wf.last_run_at
                if self._is_due(trigger_config, last_run):
                    log.info("workflow_due", workflow_id=str(wf.id), name=wf.name)
                    await self._run_workflow(wf)

    def _is_due(self, trigger_config: dict[str, Any], last_run: datetime | None) -> bool:
        """Check if a workflow is due to run."""
        trigger_type = trigger_config.get("type", "manual")
        if trigger_type == TriggerType.MANUAL:
            return False

        from app.workflows.schemas import TriggerConfig

        tc = TriggerConfig(**trigger_config)
        next_run = compute_next_run(tc, last_run)
        if next_run is None:
            return False
        return datetime.utcnow() >= next_run

    async def _run_workflow(self, workflow: Any) -> None:
        """Execute a workflow that is due."""
        from app.workflows.services.orchestrator import WorkflowOrchestrator

        orch = WorkflowOrchestrator()
        try:
            await orch.run_workflow(
                workflow_id=str(workflow.id),
                trigger_type="scheduled",
                organization_id=str(workflow.organization_id),
            )
        except Exception as exc:
            log.error("scheduled_workflow_failed", workflow_id=str(workflow.id), error=str(exc))

    def schedule_workflow(self, workflow_id: str, trigger_config: dict[str, Any]) -> dict[str, Any]:
        """Register a workflow with the scheduler. Returns next run time."""
        from app.workflows.schemas import TriggerConfig

        tc = TriggerConfig(**trigger_config)
        next_run = compute_next_run(tc)
        return {
            "workflow_id": workflow_id,
            "next_run": next_run.isoformat() if next_run else None,
            "trigger_type": tc.type,
        }


# Singleton
_scheduler: WorkflowScheduler | None = None


def get_scheduler() -> WorkflowScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = WorkflowScheduler()
    return _scheduler
