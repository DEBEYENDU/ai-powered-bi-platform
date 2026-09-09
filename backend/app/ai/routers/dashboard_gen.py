"""AI Dashboard Generator router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.dashboard.schemas import (
    TEMPLATES,
    DashboardExplainRequest,
    DashboardGenerateRequest,
    DashboardImproveRequest,
)
from app.ai.dashboard.service import AIDashboardService
from app.db.session import get_db, get_engine

dashboard_gen_router = APIRouter(prefix="/ai/dashboard", tags=["AI Dashboard Generator"])


def _get_service(db: Session = Depends(get_db)) -> AIDashboardService:
    return AIDashboardService(engine=get_engine(), db=db)


@dashboard_gen_router.post("/generate", response_model=dict[str, Any])
async def generate_dashboard(
    request: DashboardGenerateRequest = Body(...),
    service: AIDashboardService = Depends(_get_service),
):
    """Generate a complete dashboard from a natural language prompt."""
    try:
        result = await service.generate(
            prompt=request.prompt,
            organization_id=request.organization_id or "",
            save=request.save,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc


@dashboard_gen_router.post("/improve", response_model=dict[str, Any])
async def improve_dashboard(
    request: DashboardImproveRequest = Body(...),
    service: AIDashboardService = Depends(_get_service),
):
    """Improve an existing dashboard with natural language instruction."""
    try:
        result = await service.improve(
            dashboard_id=request.dashboard_id,
            instruction=request.instruction,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Improve failed: {exc}") from exc


@dashboard_gen_router.post("/explain", response_model=dict[str, Any])
async def explain_dashboard(
    request: DashboardExplainRequest = Body(...),
    service: AIDashboardService = Depends(_get_service),
):
    """Generate explanations for dashboard widgets."""
    try:
        explanations = await service.explain(
            dashboard_id=request.dashboard_id,
            widgets=request.widgets,
        )
        return {"explanations": explanations}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Explain failed: {exc}") from exc


@dashboard_gen_router.get("/templates", response_model=list[dict[str, Any]])
async def list_templates():
    """List available dashboard templates."""
    return [{"id": k, **v} for k, v in TEMPLATES.items()]


@dashboard_gen_router.get("/{dashboard_id}/versions", response_model=list[dict[str, Any]])
async def list_versions(
    dashboard_id: str,
    service: AIDashboardService = Depends(_get_service),
):
    """Get version history for a dashboard."""
    return service.get_versions(dashboard_id)


@dashboard_gen_router.post("/{dashboard_id}/rollback/{version_id}")
async def rollback_version(
    dashboard_id: str,
    version_id: str,
    service: AIDashboardService = Depends(_get_service),
):
    """Rollback a dashboard to a previous version."""
    result = service.rollback_version(dashboard_id, version_id)
    if not result:
        raise HTTPException(status_code=404, detail="Version not found")
    return result
