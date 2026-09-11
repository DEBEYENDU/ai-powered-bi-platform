"""Workflow API router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from app.workflows.ai.builder import generate_workflow
from app.workflows.monitoring.tracker import get_monitor
from app.workflows.schemas import (
    ApprovalRequest,
    WorkflowCreateRequest,
    WorkflowRunRequest,
    WorkflowUpdateRequest,
)
from app.workflows.services.orchestrator import get_orchestrator
from app.workflows.templates.defaults import get_templates
from app.workflows.validators.validator import validate_workflow

workflow_router = APIRouter(prefix="/workflows", tags=["Workflow Automation"])


def _get_user_org() -> tuple[str, str]:
    """Placeholder for auth extraction. In production, use Depends(get_current_user)."""
    return "default_user", "default_org"


# --- CRUD ---


@workflow_router.post("", response_model=dict[str, Any])
async def create_workflow(request: WorkflowCreateRequest = Body(...)) -> dict[str, Any]:
    user_id, org_id = _get_user_org()
    result = get_orchestrator().create_workflow(request, user_id, org_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Creation failed"))
    return result


@workflow_router.get("", response_model=dict[str, Any])
async def list_workflows(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    _, org_id = _get_user_org()
    return get_orchestrator().list_workflows(org_id, limit=limit, offset=offset)


@workflow_router.get("/{workflow_id}", response_model=dict[str, Any])
async def get_workflow(workflow_id: str) -> dict[str, Any]:
    _, org_id = _get_user_org()
    result = get_orchestrator().get_workflow(workflow_id, org_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@workflow_router.put("/{workflow_id}", response_model=dict[str, Any])
async def update_workflow(
    workflow_id: str, request: WorkflowUpdateRequest = Body(...)
) -> dict[str, Any]:
    _, org_id = _get_user_org()
    result = get_orchestrator().update_workflow(workflow_id, request, org_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Update failed"))
    return result


@workflow_router.delete("/{workflow_id}", response_model=dict[str, Any])
async def delete_workflow(workflow_id: str) -> dict[str, Any]:
    _, org_id = _get_user_org()
    result = get_orchestrator().delete_workflow(workflow_id, org_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


# --- Status ---


@workflow_router.post("/{workflow_id}/activate", response_model=dict[str, Any])
async def activate_workflow(workflow_id: str) -> dict[str, Any]:
    _, org_id = _get_user_org()
    result = get_orchestrator().update_status(workflow_id, "active", org_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Activation failed"))
    return result


@workflow_router.post("/{workflow_id}/pause", response_model=dict[str, Any])
async def pause_workflow(workflow_id: str) -> dict[str, Any]:
    _, org_id = _get_user_org()
    result = get_orchestrator().update_status(workflow_id, "paused", org_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Pause failed"))
    return result


# --- Execution ---


@workflow_router.post("/{workflow_id}/run", response_model=dict[str, Any])
async def run_workflow(workflow_id: str, request: WorkflowRunRequest = Body(...)) -> dict[str, Any]:
    user_id, org_id = _get_user_org()
    result = await get_orchestrator().run_workflow(
        workflow_id=workflow_id,
        trigger_type="manual",
        input_data=request.input_data,
        is_test=request.is_test,
        user_id=user_id,
        organization_id=org_id,
    )
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Execution failed"))
    return result


@workflow_router.post("/{workflow_id}/test", response_model=dict[str, Any])
async def test_workflow(
    workflow_id: str, request: WorkflowRunRequest = Body(...)
) -> dict[str, Any]:
    user_id, org_id = _get_user_org()
    result = await get_orchestrator().run_workflow(
        workflow_id=workflow_id,
        trigger_type="test",
        input_data=request.input_data,
        is_test=True,
        user_id=user_id,
        organization_id=org_id,
    )
    return result


@workflow_router.get("/{workflow_id}/executions", response_model=dict[str, Any])
async def get_executions(workflow_id: str, limit: int = 50) -> dict[str, Any]:
    return get_orchestrator().get_executions(workflow_id, limit=limit)


@workflow_router.get("/executions/{execution_id}", response_model=dict[str, Any])
async def get_execution_detail(execution_id: str) -> dict[str, Any]:
    result = get_orchestrator().get_execution_detail(execution_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


# --- Approvals ---


@workflow_router.post("/{workflow_id}/approve", response_model=dict[str, Any])
async def approve_workflow(
    workflow_id: str,
    execution_id: str = Body(..., embed=True),
    step_id: str = Body(..., embed=True),
    approval: ApprovalRequest = Body(...),
) -> dict[str, Any]:
    user_id, _ = _get_user_org()
    result = get_orchestrator().approve_step(
        execution_id=execution_id,
        step_id=step_id,
        status=approval.status,
        response=approval.response,
        user_id=user_id,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Approval failed"))
    return result


@workflow_router.post("/{workflow_id}/reject", response_model=dict[str, Any])
async def reject_workflow(
    workflow_id: str,
    execution_id: str = Body(..., embed=True),
    step_id: str = Body(..., embed=True),
    approval: ApprovalRequest = Body(...),
) -> dict[str, Any]:
    user_id, _ = _get_user_org()
    result = get_orchestrator().approve_step(
        execution_id=execution_id,
        step_id=step_id,
        status="rejected",
        response=approval.response,
        user_id=user_id,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Rejection failed"))
    return result


# --- Templates ---


@workflow_router.get("/templates/list", response_model=dict[str, Any])
async def list_templates() -> dict[str, Any]:
    templates = get_templates()
    return {"success": True, "templates": templates, "count": len(templates)}


# --- AI Builder ---


@workflow_router.post("/ai/generate", response_model=dict[str, Any])
async def ai_generate_workflow(request: dict[str, Any] = Body(...)) -> dict[str, Any]:
    prompt = request.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    result = await generate_workflow(prompt)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "AI generation failed"))

    # Validate the generated workflow
    from app.workflows.schemas import StepDefinition as SD
    from app.workflows.schemas import TriggerConfig as TC

    workflow = result.get("workflow", {})
    steps = [SD(**s) for s in workflow.get("steps", [])]
    trigger = TC(**workflow.get("trigger", {}))
    conditions = workflow.get("conditions", [])

    validation_errors = validate_workflow(workflow.get("name", ""), steps, trigger, conditions)

    return {
        "success": True,
        "workflow": workflow,
        "validation_errors": validation_errors,
        "warnings": ["This workflow was AI-generated. Please review before activating."],
    }


# --- Monitoring ---


@workflow_router.get("/monitoring/stats", response_model=dict[str, Any])
async def monitoring_stats() -> dict[str, Any]:
    monitor = get_monitor()
    stats = monitor.get_global_stats()
    return {"success": True, **stats}


@workflow_router.get("/monitoring/recent", response_model=dict[str, Any])
async def monitoring_recent(limit: int = 50) -> dict[str, Any]:
    monitor = get_monitor()
    executions = monitor.get_recent_executions(limit=limit)
    return {"success": True, "executions": executions, "count": len(executions)}
