"""Autonomous BI Copilot API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.copilot.schemas.request import CopilotQueryRequest
from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization
from app.exceptions.handlers import AppError, NotFoundError

copilot_router = APIRouter(prefix="/copilot", tags=["Autonomous BI Copilot"])


@copilot_router.post("/query")
async def copilot_query(
    request: CopilotQueryRequest = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Send a natural language request to the BI Copilot.

    The copilot will:
    1. Understand your intent
    2. Create an execution plan
    3. Execute the necessary tools (SQL, RAG, analysis, etc.)
    4. Validate results
    5. Provide a business insight answer
    """
    from app.copilot.services.copilot_service import CopilotService

    service = CopilotService(db)
    result = await service.process_query(
        query=request.query,
        user=user,
        organization_id=organization_id,
        session_id=request.session_id,
    )
    # Audit log
    try:
        from app.admin.services.platform import PlatformAdmin

        platform = PlatformAdmin()
        platform.audit.append(
            action="copilot_query",
            resource_type="copilot_task",
            resource_id=result.task_id,
            actor_id=user.get("sub"),
            organization_id=organization_id,
            details={
                "query": request.query[:200],
                "intent": result.intent,
                "status": result.status,
            },
        )
    except Exception:
        pass
    # Metrics
    try:
        from app.admin.services.platform import PlatformAdmin

        platform = PlatformAdmin()
        platform.metrics.record(
            "copilot_requests_total", 1.0, labels={"intent": result.intent or "unknown"}
        )
    except Exception:
        pass
    return result


@copilot_router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Get copilot task status and results."""
    from app.copilot.services.copilot_service import CopilotService

    service = CopilotService(db)
    result = service.get_task(task_id, organization_id)
    if not result:
        raise NotFoundError("Task not found")
    return result


@copilot_router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Cancel a running copilot task."""
    from app.copilot.services.copilot_service import CopilotService

    service = CopilotService(db)
    success = service.cancel_task(task_id, organization_id)
    if not success:
        raise AppError("Task cannot be cancelled (not found or already completed)")
    return {"success": True, "task_id": task_id, "status": "cancelled"}


@copilot_router.get("/sessions")
async def list_sessions(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """List copilot sessions for the current user."""
    from app.copilot.services.copilot_service import CopilotService

    service = CopilotService(db)
    sessions = service.list_sessions(user.get("sub") or user.get("user_id", ""), organization_id)
    return {"data": sessions, "total": len(sessions)}


@copilot_router.post("/sessions", status_code=201)
async def create_session(
    title: str = Body("New Session"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Create a new copilot session."""
    from app.copilot.models.session import CopilotSession

    session = CopilotSession(
        organization_id=organization_id,
        user_id=user.get("sub") or user.get("user_id", ""),
        title=title,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "title": session.title, "created_at": str(session.created_at)}


@copilot_router.get("/tools")
async def list_tools():
    """List available copilot tools."""
    from app.copilot.tools.registry import ToolRegistry

    registry = ToolRegistry.get_instance()
    return {"tools": registry.list_tools()}
