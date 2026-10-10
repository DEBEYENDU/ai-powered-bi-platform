"""AI Report Generator router — /ai/reports endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.ai.reports.schemas import (
    GenerateReportRequest,
    ReportFollowUpRequest,
)
from app.ai.reports.services.report_service import ReportGeneratorService
from app.db.session import get_db, get_engine
from app.dependencies.deps import get_current_user, require_organization

ai_reports_router = APIRouter(prefix="/ai/reports", tags=["AI Report Generator"])


def _get_service(db: Session = Depends(get_db)) -> ReportGeneratorService:
    return ReportGeneratorService(engine=get_engine(), db=db)


@ai_reports_router.post("/generate", response_model=dict[str, Any])
async def generate_report(
    request: GenerateReportRequest = Body(...),
    service: ReportGeneratorService = Depends(_get_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Generate a professional business report from a natural language prompt."""
    try:
        result = await service.generate(
            prompt=request.prompt,
            dashboard_id=request.dashboard_id,
            report_type=request.report_type.value
            if hasattr(request.report_type, "value")
            else request.report_type,
            formats=[f.value if hasattr(f, "value") else f for f in request.formats],
            branding=request.branding,
            organization_id=organization_id,
            owner_id=str(user.get("sub", "") or ""),
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}") from exc


@ai_reports_router.get("", response_model=dict[str, Any])
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    report_type: str | None = Query(None),
    service: ReportGeneratorService = Depends(_get_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """List AI-generated reports with search, filter, and pagination."""
    return service.list_reports(
        page=page, page_size=page_size, search=search, report_type=report_type,
        organization_id=organization_id,
    )


@ai_reports_router.get("/{report_id}", response_model=dict[str, Any])
async def get_report(
    report_id: str,
    service: ReportGeneratorService = Depends(_get_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Get a single AI report by ID."""
    result = service.get_report(report_id, organization_id=organization_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return result


@ai_reports_router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    service: ReportGeneratorService = Depends(_get_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Soft-delete an AI report."""
    success = service.delete_report(report_id, organization_id=organization_id)
    if not success:
        raise HTTPException(status_code=404, detail="Report not found or delete failed")
    return {"success": True, "report_id": report_id}


@ai_reports_router.post("/followup", response_model=dict[str, Any])
async def followup_question(
    request: ReportFollowUpRequest = Body(...),
    service: ReportGeneratorService = Depends(_get_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Ask a follow-up question about a generated report."""
    try:
        return await service.followup(request.report_id, request.question, organization_id=organization_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Follow-up failed: {exc}") from exc


@ai_reports_router.get("/templates/list", response_model=list[dict[str, Any]])
async def list_templates(
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """List available report type templates."""
    from app.ai.reports.templates.registry import list_templates

    return list_templates()
