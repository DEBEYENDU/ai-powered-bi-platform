"""Multi-Agent AI Platform router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.agents.schemas import AgentRunRequest
from app.ai.agents.services import orchestrator
from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization

agents_router = APIRouter(prefix="/ai/agents", tags=["AI Multi-Agent Platform"])


def _dataset_context(db: Session, organization_id: str) -> dict[str, Any]:
    """Real dataset inventory for the agent context, so agents answer from
    the organization's actual data instead of claiming none exists."""
    try:
        from app.ai.data_engineering.services.dataset_store import list_datasets

        records = list_datasets(db, organization_id)
        listing = "\n".join(
            f"- {r.name}: {r.row_count} rows, {r.column_count} columns"
            for r in records[:20]
        )
        return {
            "datasets": [
                {
                    "id": str(r.id),
                    "name": r.name,
                    "rows": r.row_count,
                    "columns": r.column_count,
                }
                for r in records[:20]
            ],
            "data_summary": listing or "No datasets uploaded yet for this organization.",
        }
    except Exception:  # noqa: BLE001 — grounding is best-effort
        return {}


@agents_router.post("/run", response_model=dict[str, Any])
async def run_task(
    request: AgentRunRequest = Body(...),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Execute a task using the multi-agent system."""
    request.context = {**_dataset_context(db, organization_id), **(request.context or {})}
    try:
        result = await orchestrator.run_agent_task(request)
        return result.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}") from exc


@agents_router.get("/agents", response_model=dict[str, Any])
async def list_agents(user: dict = Depends(get_current_user), organization_id: str = Depends(require_organization)) -> dict[str, Any]:
    """Get status of all registered agents."""
    result = orchestrator.get_agent_list()
    return result.model_dump()


@agents_router.get("/tasks", response_model=dict[str, Any])
async def task_history(limit: int = 50, user: dict = Depends(get_current_user), organization_id: str = Depends(require_organization)) -> dict[str, Any]:
    """Get execution task history."""
    result = orchestrator.get_task_history(limit=limit)
    return result.model_dump()


@agents_router.get("/logs", response_model=dict[str, Any])
async def agent_logs(
    task_id: str | None = None,
    agent_type: str | None = None,
    level: str | None = None,
    limit: int = 100,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Get filtered agent logs."""
    result = orchestrator.get_agent_logs(
        task_id=task_id,
        agent_type=agent_type,
        level=level,
        limit=limit,
    )
    return result.model_dump()


@agents_router.get("/memory", response_model=dict[str, Any])
async def memory_entries(
    session_id: str | None = None,
    task_id: str | None = None,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Get memory entries."""
    result = orchestrator.get_memory_entries(session_id=session_id, task_id=task_id)
    return result.model_dump()


@agents_router.get("/metrics", response_model=dict[str, Any])
async def agent_metrics(agent_type: str | None = None, user: dict = Depends(get_current_user), organization_id: str = Depends(require_organization)) -> dict[str, Any]:
    """Get agent performance metrics."""
    return orchestrator.get_agent_metrics(agent_type)


@agents_router.get("/stats", response_model=dict[str, Any])
async def system_stats(user: dict = Depends(get_current_user), organization_id: str = Depends(require_organization)) -> dict[str, Any]:
    """Get overall system statistics."""
    return {
        "agent_metrics": orchestrator.get_agent_metrics(),
        "memory_stats": orchestrator.get_memory_stats(),
    }
