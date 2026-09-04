"""FastAPI routers for the Reporting Engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.reports.schemas.report import (
    ReportCreate,
    ReportGenerateRequest,
    ScheduleCreate,
    ShareCreate,
    TemplateApprove,
    TemplateCreate,
)
from app.reports.services.report_service import ReportService

reports_router = APIRouter(prefix="/reports", tags=["Reports"])


def get_service() -> ReportService:
    return ReportService()


def _record_to_out(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "title": record.get("title"),
        "report_type": record.get("report_type", "custom"),
        "status": record.get("status", "draft"),
        "current_version": record.get("current_version", 0),
        "tags": record.get("tags", []),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


@reports_router.post("", summary="Create report")
def create_report(payload: ReportCreate = Body(...), service: ReportService = Depends(get_service)):
    record = service.create_report(payload.dict())
    return _record_to_out(record)


@reports_router.get("", summary="List reports")
def list_reports(
    report_type: str | None = Query(None),
    status: str | None = Query(None),
    search: str = Query(""),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: ReportService = Depends(get_service),
):
    records = service.repo.list(
        report_type=report_type, status=status, search=search, limit=limit, offset=offset
    )
    return {
        "data": [_record_to_out(r) for r in records],
        "meta": {"limit": limit, "offset": offset},
    }


@reports_router.get("/search", summary="Search reports")
def search_reports(
    query: str = Query(""),
    report_type: str | None = Query(None),
    status: str | None = Query(None),
    service: ReportService = Depends(get_service),
):
    records = service.repo.list(report_type=report_type, status=status, search=query)
    return {"data": [_record_to_out(r) for r in records]}


@reports_router.get("/{report_id}", summary="Get report")
def get_report(report_id: str, service: ReportService = Depends(get_service)):
    record = service.repo.get(report_id)
    if record is None:
        raise HTTPException(404, "Report not found")
    return _record_to_out(record)


@reports_router.post("/generate", summary="Generate report")
async def generate_report(
    payload: ReportGenerateRequest = Body(...), service: ReportService = Depends(get_service)
):
    try:
        return await service.generate(
            report_id=str(payload.report_id) if payload.report_id else None,
            definition=payload.definition.dict() if payload.definition else None,
            formats=payload.formats,
            include_ai=payload.include_ai,
            ai_sections=payload.ai_sections,
            variables=payload.variables,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@reports_router.post("/preview", summary="Preview report HTML")
def preview_report(
    definition: dict[str, Any] = Body(...), service: ReportService = Depends(get_service)
):
    from fastapi.responses import HTMLResponse

    return HTMLResponse(service.preview(definition))


@reports_router.get("/{report_id}/download", summary="Download artifact")
def download_report(
    report_id: str,
    format: str = Query("pdf"),
    version: int = Query(0),
    service: ReportService = Depends(get_service),
):
    record = service.repo.get(report_id)
    if record is None:
        raise HTTPException(404, "Report not found")
    versions = service.repo.versions(report_id)
    if not versions:
        raise HTTPException(404, "No generated versions yet")
    target = (
        versions[-1]
        if version == 0
        else next((v for v in versions if v["version_number"] == version), None)
    )
    if target is None:
        raise HTTPException(404, "Version not found")
    path = target.get("storage_paths", {}).get(format.lower())
    if not path or not Path(path).exists():
        raise HTTPException(404, f"Format '{format}' not generated for this version")
    service._log("report_downloaded", report_id, "", "", {"format": format})
    return FileResponse(path)


@reports_router.get("/{report_id}/versions", summary="List versions")
def list_versions(report_id: str, service: ReportService = Depends(get_service)):
    return {"data": service.repo.versions(report_id)}


@reports_router.get("/{report_id}/versions/compare", summary="Compare versions")
def compare_versions(
    report_id: str,
    from_version: int = Query(...),
    to_version: int = Query(...),
    service: ReportService = Depends(get_service),
):
    return service.repo.compare(report_id, from_version, to_version)


@reports_router.post("/{report_id}/restore/{version}", summary="Restore version")
def restore_version(report_id: str, version: int, service: ReportService = Depends(get_service)):
    record = service.repo.get(report_id)
    if record is None:
        raise HTTPException(404, "Report not found")
    versions = {v["version_number"]: v for v in service.repo.versions(report_id)}
    snapshot = versions.get(version)
    if snapshot is None:
        raise HTTPException(404, "Version not found")
    service.repo.update(report_id, {"definition": snapshot.get("definition_snapshot", {})})
    return {"restored": version}


@reports_router.post("/{report_id}/approve", summary="Approve report")
def approve_report(
    report_id: str, approved_by: str = Body(""), service: ReportService = Depends(get_service)
):
    record = service.repo.update(report_id, {"status": "published"})
    if record is None:
        raise HTTPException(404, "Report not found")
    service.events.publish("approval_granted", report_id, approved_by, details={})
    return _record_to_out(record)


@reports_router.post("/{report_id}/archive", summary="Archive report")
def archive_report(report_id: str, service: ReportService = Depends(get_service)):
    if not service.repo.delete(report_id):
        raise HTTPException(404, "Report not found")
    service.events.publish("report_archived", report_id, details={})
    return {"archived": True}


@reports_router.post("/{report_id}/share", summary="Share report")
def share_report(
    report_id: str, payload: ShareCreate = Body(...), service: ReportService = Depends(get_service)
):
    return service.permissions.grant(
        report_id, payload.granted_to, payload.role, payload.can_export, payload.can_distribute
    )


@reports_router.post("/schedules", summary="Schedule report")
def create_schedule(
    payload: ScheduleCreate = Body(...), service: ReportService = Depends(get_service)
):
    sched = service.scheduler.create(
        report_id=str(payload.report_id),
        frequency=payload.frequency,
        cron_expression=payload.cron_expression,
        timezone=payload.timezone,
        distribution=payload.distribution,
        max_retries=payload.max_retries,
    )
    service.events.publish(
        "report_scheduled", str(payload.report_id), details={"schedule_id": sched.schedule_id}
    )
    return sched.dict()


@reports_router.delete("/schedules/{schedule_id}", summary="Cancel schedule")
def cancel_schedule(schedule_id: str, service: ReportService = Depends(get_service)):
    if not service.scheduler.cancel(schedule_id):
        raise HTTPException(404, "Schedule not found")
    return {"cancelled": True}


@reports_router.post("/schedules/{schedule_id}/pause", summary="Pause schedule")
def pause_schedule(schedule_id: str, service: ReportService = Depends(get_service)):
    if not service.scheduler.pause(schedule_id):
        raise HTTPException(404, "Schedule not found")
    return {"paused": True}


@reports_router.post("/schedules/{schedule_id}/resume", summary="Resume schedule")
def resume_schedule(schedule_id: str, service: ReportService = Depends(get_service)):
    if not service.scheduler.resume(schedule_id):
        raise HTTPException(404, "Schedule not found")
    return {"resumed": True}


@reports_router.post("/templates", summary="Create template")
def create_template(
    payload: TemplateCreate = Body(...), service: ReportService = Depends(get_service)
):
    tpl = service.templates.create(
        payload.name,
        payload.description,
        layout={},
        sections=[s.dict() for s in payload.sections],
        shared=payload.shared,
    )
    return {
        "id": tpl.template_id,
        "name": tpl.name,
        "current_version": 1,
        "approved": False,
        "shared": tpl.shared,
    }


@reports_router.get("/templates/list", summary="List templates")
def list_templates(service: ReportService = Depends(get_service)):
    return {
        "data": [
            {
                "id": t.template_id,
                "name": t.name,
                "current_version": t.current_version,
                "shared": t.shared,
            }
            for t in service.templates.list()
        ]
    }


@reports_router.post("/templates/{template_id}/approve", summary="Approve template")
def approve_template(
    template_id: str,
    payload: TemplateApprove = Body(...),
    service: ReportService = Depends(get_service),
):
    tpl = service.templates.get(template_id)
    if tpl is None:
        raise HTTPException(404, "Template not found")
    ok = service.templates.approve(template_id, tpl.current_version, payload.approved_by)
    service.events.publish(
        "template_updated", None, payload.approved_by, details={"template_id": template_id}
    )
    return {"approved": ok}


@reports_router.get("/{report_id}/history", summary="Report history")
def report_history(report_id: str, service: ReportService = Depends(get_service)):
    return {
        "data": [e.dict() for e in service.events.history(report_id)]
        + service.audit_trail(report_id)
    }


@reports_router.get("/{report_id}/deliveries", summary="Delivery status")
def delivery_status(report_id: str, service: ReportService = Depends(get_service)):
    return {"data": [a.dict() for a in service.distribution.attempts(report_id)]}
