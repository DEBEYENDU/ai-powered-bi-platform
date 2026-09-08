"""Dashboard FastAPI router (mounted under /api/v1 + legacy alias)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from app.admin.services.platform import get_platform
from app.dashboards import service
from app.dashboards.schemas import DashboardCreate, DashboardShare, DashboardUpdate

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


def _platform():
    return get_platform()


@router.post("", summary="Create dashboard")
def create_dashboard(payload: DashboardCreate = Body(...)):
    _platform()
    try:
        return service.create_dashboard(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("", summary="List dashboards")
def list_dashboards(
    organization_id: str | None = Query(None),
    include_archived: bool = Query(False),
):
    _platform()
    try:
        return {"data": service.list_dashboards(organization_id, include_archived)}
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/counts", summary="Dashboard counts")
def dashboard_counts():
    _platform()
    try:
        items = service.list_dashboards(include_archived=True)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {
        "total": len(items),
        "active": sum(1 for d in items if not d["archived"]),
        "shared": sum(1 for d in items if d["shared"]),
    }


@router.get("/{dashboard_id}", summary="Get dashboard")
def get_dashboard(dashboard_id: str):
    _platform()
    try:
        record = service.get_dashboard(dashboard_id)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    if record is None:
        raise HTTPException(404, "Dashboard not found")
    return record


@router.patch("/{dashboard_id}", summary="Update dashboard")
def update_dashboard(dashboard_id: str, payload: DashboardUpdate = Body(...)):
    _platform()
    try:
        record = service.update_dashboard(dashboard_id, payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if record is None:
        raise HTTPException(404, "Dashboard not found")
    return record


@router.post("/{dashboard_id}/share", summary="Share or unshare dashboard")
def share_dashboard(dashboard_id: str, payload: DashboardShare = Body(...)):
    _platform()
    try:
        record = service.update_dashboard(dashboard_id, {"shared": payload.shared})
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if record is None:
        raise HTTPException(404, "Dashboard not found")
    return record


@router.post("/{dashboard_id}/archive", summary="Archive dashboard")
def archive_dashboard(dashboard_id: str):
    _platform()
    try:
        record = service.archive_dashboard(dashboard_id, True)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    if record is None:
        raise HTTPException(404, "Dashboard not found")
    return record


@router.post("/{dashboard_id}/restore", summary="Restore dashboard")
def restore_dashboard(dashboard_id: str):
    _platform()
    try:
        record = service.archive_dashboard(dashboard_id, False)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    if record is None:
        raise HTTPException(404, "Dashboard not found")
    return record


@router.delete("/{dashboard_id}", summary="Delete dashboard")
def delete_dashboard(dashboard_id: str):
    _platform()
    try:
        ok = service.delete_dashboard(dashboard_id)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    if not ok:
        raise HTTPException(404, "Dashboard not found")
    return {"deleted": True}


@router.post("/validate-widgets", summary="Validate widget definitions")
def validate_widgets(widgets: list[dict[str, Any]] = Body(...)):
    _platform()
    try:
        service._validate_widgets(widgets)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"valid": True, "count": len(widgets)}
