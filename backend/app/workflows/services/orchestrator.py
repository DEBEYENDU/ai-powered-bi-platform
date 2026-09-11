"""Main workflow orchestrator service."""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any

from app.core.logging import get_logger
from app.workflows.engine.executor import get_engine
from app.workflows.monitoring.tracker import get_monitor
from app.workflows.schemas import (
    ExecutionStatus,
    StepDefinition,
    TriggerConfig,
    WorkflowCreateRequest,
    WorkflowStatus,
    WorkflowUpdateRequest,
)
from app.workflows.validators.validator import validate_workflow

log = get_logger("workflow.orchestrator")


class WorkflowOrchestrator:
    """Main service layer for workflow operations."""

    def create_workflow(
        self, request: WorkflowCreateRequest, user_id: str, organization_id: str
    ) -> dict[str, Any]:
        """Create a new workflow."""
        errors = validate_workflow(request.name, request.steps, request.trigger, request.conditions)
        if errors:
            return {"success": False, "error": "; ".join(errors)}

        workflow_id = str(uuid.uuid4())[:12]

        from app.db.session import get_db_session
        from app.workflows.models import WorkflowRecord

        with get_db_session() as db:
            if db is None:
                return {"success": False, "error": "Database unavailable"}

            wf = WorkflowRecord(
                id=workflow_id,
                organization_id=organization_id,
                created_by=user_id,
                name=request.name,
                description=request.description,
                status=WorkflowStatus.DRAFT,
                trigger_config=request.trigger.model_dump(),
                steps=[s.model_dump() for s in request.steps],
                conditions=[c.model_dump() for c in request.conditions],
                schedule=request.schedule,
                variables=request.variables,
                tags=request.tags,
                max_retries=request.max_retries,
                timeout_seconds=request.timeout_seconds,
            )
            db.add(wf)
            db.commit()

        log.info("workflow_created", workflow_id=workflow_id, name=request.name)
        return {
            "success": True,
            "workflow_id": workflow_id,
            "name": request.name,
            "status": "draft",
        }

    def get_workflow(self, workflow_id: str, organization_id: str) -> dict[str, Any]:
        """Get a workflow by ID."""
        from app.db.session import get_db_session
        from app.workflows.models import WorkflowRecord

        with get_db_session() as db:
            if db is None:
                return {"success": False, "error": "Database unavailable"}

            wf = (
                db.query(WorkflowRecord)
                .filter(
                    WorkflowRecord.id == workflow_id,
                    WorkflowRecord.organization_id == organization_id,
                    WorkflowRecord.deleted_at.is_(None),
                )
                .first()
            )

            if not wf:
                return {"success": False, "error": "Workflow not found"}

            return {
                "success": True,
                "id": str(wf.id),
                "name": wf.name,
                "description": wf.description,
                "status": wf.status,
                "trigger": wf.trigger_config or {},
                "steps": wf.steps or [],
                "conditions": wf.conditions or [],
                "schedule": wf.schedule or {},
                "variables": wf.variables or {},
                "tags": wf.tags or [],
                "max_retries": wf.max_retries,
                "timeout_seconds": wf.timeout_seconds,
                "last_run_at": wf.last_run_at.isoformat() if wf.last_run_at else None,
                "next_run_at": wf.next_run_at.isoformat() if wf.next_run_at else None,
                "created_at": wf.created_at.isoformat() if wf.created_at else "",
                "updated_at": wf.updated_at.isoformat() if wf.updated_at else "",
            }

    def list_workflows(
        self, organization_id: str, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        """List workflows for an organization."""
        from app.db.session import get_db_session
        from app.workflows.models import WorkflowRecord

        with get_db_session() as db:
            if db is None:
                return {"success": False, "error": "Database unavailable"}

            query = db.query(WorkflowRecord).filter(
                WorkflowRecord.organization_id == organization_id,
                WorkflowRecord.deleted_at.is_(None),
            )
            total = query.count()
            workflows = (
                query.order_by(WorkflowRecord.created_at.desc()).offset(offset).limit(limit).all()
            )

            return {
                "success": True,
                "workflows": [
                    {
                        "id": str(wf.id),
                        "name": wf.name,
                        "description": wf.description,
                        "status": wf.status,
                        "tags": wf.tags or [],
                        "last_run_at": wf.last_run_at.isoformat() if wf.last_run_at else None,
                        "next_run_at": wf.next_run_at.isoformat() if wf.next_run_at else None,
                        "created_at": wf.created_at.isoformat() if wf.created_at else "",
                    }
                    for wf in workflows
                ],
                "count": total,
            }

    def update_workflow(
        self, workflow_id: str, request: WorkflowUpdateRequest, organization_id: str
    ) -> dict[str, Any]:
        """Update a workflow."""
        from app.db.session import get_db_session
        from app.workflows.models import WorkflowRecord

        with get_db_session() as db:
            if db is None:
                return {"success": False, "error": "Database unavailable"}

            wf = (
                db.query(WorkflowRecord)
                .filter(
                    WorkflowRecord.id == workflow_id,
                    WorkflowRecord.organization_id == organization_id,
                    WorkflowRecord.deleted_at.is_(None),
                )
                .first()
            )

            if not wf:
                return {"success": False, "error": "Workflow not found"}

            if request.name is not None:
                wf.name = request.name
            if request.description is not None:
                wf.description = request.description
            if request.trigger is not None:
                wf.trigger_config = request.trigger.model_dump()
            if request.steps is not None:
                wf.steps = [s.model_dump() for s in request.steps]
            if request.conditions is not None:
                wf.conditions = [c.model_dump() for c in request.conditions]
            if request.schedule is not None:
                wf.schedule = request.schedule
            if request.variables is not None:
                wf.variables = request.variables
            if request.tags is not None:
                wf.tags = request.tags
            if request.max_retries is not None:
                wf.max_retries = request.max_retries
            if request.timeout_seconds is not None:
                wf.timeout_seconds = request.timeout_seconds

            wf.updated_at = datetime.utcnow()
            db.commit()

        return {"success": True, "message": "Workflow updated"}

    def delete_workflow(self, workflow_id: str, organization_id: str) -> dict[str, Any]:
        """Soft-delete a workflow."""
        from app.db.session import get_db_session
        from app.workflows.models import WorkflowRecord

        with get_db_session() as db:
            if db is None:
                return {"success": False, "error": "Database unavailable"}

            wf = (
                db.query(WorkflowRecord)
                .filter(
                    WorkflowRecord.id == workflow_id,
                    WorkflowRecord.organization_id == organization_id,
                    WorkflowRecord.deleted_at.is_(None),
                )
                .first()
            )

            if not wf:
                return {"success": False, "error": "Workflow not found"}

            wf.deleted_at = datetime.utcnow()
            wf.status = WorkflowStatus.DISABLED
            db.commit()

        return {"success": True, "message": "Workflow deleted"}

    def update_status(self, workflow_id: str, status: str, organization_id: str) -> dict[str, Any]:
        """Update workflow status (activate, pause, disable)."""
        from app.db.session import get_db_session
        from app.workflows.models import WorkflowRecord

        with get_db_session() as db:
            if db is None:
                return {"success": False, "error": "Database unavailable"}

            wf = (
                db.query(WorkflowRecord)
                .filter(
                    WorkflowRecord.id == workflow_id,
                    WorkflowRecord.organization_id == organization_id,
                    WorkflowRecord.deleted_at.is_(None),
                )
                .first()
            )

            if not wf:
                return {"success": False, "error": "Workflow not found"}

            wf.status = status
            wf.updated_at = datetime.utcnow()

            # Compute next_run_at if activating
            if status == WorkflowStatus.ACTIVE:
                trigger_config = wf.trigger_config or {}
                if trigger_config.get("type") != "manual":
                    from app.workflows.triggers.handler import compute_next_run

                    tc = TriggerConfig(**trigger_config)
                    next_run = compute_next_run(tc)
                    wf.next_run_at = next_run

            db.commit()

        log.info("workflow_status_changed", workflow_id=workflow_id, status=status)
        return {"success": True, "status": status}

    async def run_workflow(
        self,
        workflow_id: str,
        trigger_type: str = "manual",
        input_data: dict[str, Any] | None = None,
        is_test: bool = False,
        user_id: str = "",
        organization_id: str = "",
    ) -> dict[str, Any]:
        """Execute a workflow."""
        from app.db.session import get_db_session
        from app.workflows.models import WorkflowExecutionRecord, WorkflowRecord

        # Load workflow
        with get_db_session() as db:
            if db is None:
                return {"success": False, "error": "Database unavailable"}

            wf = (
                db.query(WorkflowRecord)
                .filter(
                    WorkflowRecord.id == workflow_id,
                    WorkflowRecord.deleted_at.is_(None),
                )
                .first()
            )

            if not wf:
                return {"success": False, "error": "Workflow not found"}

            steps_raw = wf.steps or []
            conditions_raw = wf.conditions or []
            wf_max_retries = wf.max_retries
            wf_timeout = wf.timeout_seconds

        # Build step definitions
        steps = [StepDefinition(**s) for s in steps_raw]

        # Create execution record
        execution_id = str(uuid.uuid4())[:12]
        idempotency_key = f"{workflow_id}:{trigger_type}:{int(time.time())}"

        with get_db_session() as db:
            if db:
                exec_record = WorkflowExecutionRecord(
                    id=execution_id,
                    workflow_id=workflow_id,
                    organization_id=organization_id,
                    triggered_by=user_id or "system",
                    trigger_type=trigger_type,
                    status=ExecutionStatus.RUNNING,
                    is_test=is_test,
                    input_data=input_data or {},
                    idempotency_key=idempotency_key,
                )
                db.add(exec_record)
                db.commit()

        # Execute workflow
        engine = get_engine()
        result = await engine.execute_workflow(
            workflow_id=workflow_id,
            steps=steps,
            conditions=conditions_raw,
            input_data=input_data or {},
            max_retries=wf_max_retries,
            timeout_seconds=wf_timeout,
            is_test=is_test,
            organization_id=organization_id,
        )

        # Update execution record
        with get_db_session() as db:
            if db:
                exec_record = (
                    db.query(WorkflowExecutionRecord)
                    .filter(WorkflowExecutionRecord.id == execution_id)
                    .first()
                )
                if exec_record:
                    exec_record.status = result["status"]
                    exec_record.output_data = result.get("output_data", {})
                    exec_record.errors = result.get("errors", [])
                    exec_record.duration_ms = result.get("duration_ms", 0)
                    exec_record.completed_at = datetime.utcnow()
                    db.commit()

        # Update workflow last_run_at
        with get_db_session() as db:
            if db:
                wf_rec = db.query(WorkflowRecord).filter(WorkflowRecord.id == workflow_id).first()
                if wf_rec:
                    wf_rec.last_run_at = datetime.utcnow()
                    db.commit()

        # Record metrics
        monitor = get_monitor()
        monitor.record_execution(
            workflow_id=workflow_id,
            status=result["status"],
            duration_ms=result.get("duration_ms", 0),
            execution_id=execution_id,
        )

        return {
            "success": result["status"] == ExecutionStatus.COMPLETED,
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": result["status"],
            "output_data": result.get("output_data", {}),
            "errors": result.get("errors", []),
            "duration_ms": result.get("duration_ms", 0),
            "steps": result.get("steps", []),
        }

    def get_executions(self, workflow_id: str, limit: int = 50) -> dict[str, Any]:
        """Get execution history for a workflow."""
        from app.db.session import get_db_session
        from app.workflows.models import WorkflowExecutionRecord

        with get_db_session() as db:
            if db is None:
                return {"success": False, "error": "Database unavailable"}

            execs = (
                db.query(WorkflowExecutionRecord)
                .filter(
                    WorkflowExecutionRecord.workflow_id == workflow_id,
                )
                .order_by(WorkflowExecutionRecord.created_at.desc())
                .limit(limit)
                .all()
            )

            return {
                "success": True,
                "executions": [
                    {
                        "id": str(e.id),
                        "status": e.status,
                        "trigger_type": e.trigger_type,
                        "is_test": e.is_test,
                        "duration_ms": e.duration_ms,
                        "errors": e.errors or [],
                        "started_at": e.started_at.isoformat() if e.started_at else "",
                        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                    }
                    for e in execs
                ],
                "count": len(execs),
            }

    def get_execution_detail(self, execution_id: str) -> dict[str, Any]:
        """Get detailed execution info including step-level results."""
        from app.db.session import get_db_session
        from app.workflows.models import WorkflowExecutionRecord, WorkflowStepExecutionRecord

        with get_db_session() as db:
            if db is None:
                return {"success": False, "error": "Database unavailable"}

            exec_rec = (
                db.query(WorkflowExecutionRecord)
                .filter(WorkflowExecutionRecord.id == execution_id)
                .first()
            )

            if not exec_rec:
                return {"success": False, "error": "Execution not found"}

            steps = (
                db.query(WorkflowStepExecutionRecord)
                .filter(WorkflowStepExecutionRecord.execution_id == execution_id)
                .order_by(WorkflowStepExecutionRecord.created_at)
                .all()
            )

            return {
                "success": True,
                "id": str(exec_rec.id),
                "workflow_id": str(exec_rec.workflow_id),
                "status": exec_rec.status,
                "trigger_type": exec_rec.trigger_type,
                "is_test": exec_rec.is_test,
                "input_data": exec_rec.input_data or {},
                "output_data": exec_rec.output_data or {},
                "errors": exec_rec.errors or [],
                "duration_ms": exec_rec.duration_ms,
                "started_at": exec_rec.started_at.isoformat() if exec_rec.started_at else "",
                "completed_at": exec_rec.completed_at.isoformat()
                if exec_rec.completed_at
                else None,
                "steps": [
                    {
                        "id": str(s.id),
                        "step_id": s.step_id,
                        "step_name": s.step_name,
                        "action_type": s.action_type,
                        "status": s.status,
                        "input_data": s.input_data or {},
                        "output_data": s.output_data or {},
                        "error": s.error,
                        "retry_count": s.retry_count,
                        "duration_ms": s.duration_ms,
                        "started_at": s.started_at.isoformat() if s.started_at else None,
                        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    }
                    for s in steps
                ],
            }

    def approve_step(
        self, execution_id: str, step_id: str, status: str, response: str, user_id: str
    ) -> dict[str, Any]:
        """Approve or reject a pending approval step."""
        from app.db.session import get_db_session
        from app.workflows.models import WorkflowApprovalRecord

        with get_db_session() as db:
            if db is None:
                return {"success": False, "error": "Database unavailable"}

            approval = (
                db.query(WorkflowApprovalRecord)
                .filter(
                    WorkflowApprovalRecord.execution_id == execution_id,
                    WorkflowApprovalRecord.step_id == step_id,
                    WorkflowApprovalRecord.status == "pending",
                )
                .first()
            )

            if not approval:
                return {"success": False, "error": "No pending approval found"}

            approval.status = status
            approval.response = response
            approval.resolved_at = datetime.utcnow()
            db.commit()

        log.info("approval_resolved", execution_id=execution_id, step_id=step_id, status=status)
        return {"success": True, "status": status}


# Singleton
_orchestrator: WorkflowOrchestrator | None = None


def get_orchestrator() -> WorkflowOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = WorkflowOrchestrator()
    return _orchestrator
