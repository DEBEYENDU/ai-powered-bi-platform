"""Dashboard FastAPI router (mounted under /api/v1 + legacy alias)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.admin.services.platform import get_platform
from app.dashboards import service
from app.dashboards.schemas import DashboardCreate, DashboardShare, DashboardUpdate
from app.dependencies.deps import get_current_user, require_organization

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


def _platform():
    return get_platform()


@router.post("", summary="Create dashboard")
def create_dashboard(
    payload: DashboardCreate = Body(...),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    _platform()
    try:
        data = payload.model_dump()
        data["organization_id"] = data.get("organization_id") or organization_id
        return service.create_dashboard(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("", summary="List dashboards")
def list_dashboards(
    organization_id: str | None = Query(None),
    include_archived: bool = Query(False),
    user: dict = Depends(get_current_user),
    auth_org: str = Depends(require_organization),
):
    _platform()
    try:
        return {"data": service.list_dashboards(organization_id or auth_org, include_archived)}
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/counts", summary="Dashboard counts")
def dashboard_counts(
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
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
def get_dashboard(
    dashboard_id: str,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    _platform()
    try:
        record = service.get_dashboard(dashboard_id, organization_id)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    if record is None:
        raise HTTPException(404, "Dashboard not found")
    return record


@router.patch("/{dashboard_id}", summary="Update dashboard")
def update_dashboard(
    dashboard_id: str,
    payload: DashboardUpdate = Body(...),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    _platform()
    try:
        record = service.update_dashboard(
            dashboard_id, payload.model_dump(exclude_none=True), organization_id
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if record is None:
        raise HTTPException(404, "Dashboard not found")
    return record


@router.post("/{dashboard_id}/share", summary="Share or unshare dashboard")
def share_dashboard(
    dashboard_id: str,
    payload: DashboardShare = Body(...),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    _platform()
    try:
        record = service.update_dashboard(
            dashboard_id, {"shared": payload.shared}, organization_id
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if record is None:
        raise HTTPException(404, "Dashboard not found")
    return record


@router.post("/{dashboard_id}/archive", summary="Archive dashboard")
def archive_dashboard(
    dashboard_id: str,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    _platform()
    try:
        record = service.archive_dashboard(dashboard_id, True, organization_id)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    if record is None:
        raise HTTPException(404, "Dashboard not found")
    return record


@router.post("/{dashboard_id}/restore", summary="Restore dashboard")
def restore_dashboard(
    dashboard_id: str,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    _platform()
    try:
        record = service.archive_dashboard(dashboard_id, False, organization_id)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    if record is None:
        raise HTTPException(404, "Dashboard not found")
    return record


@router.delete("/{dashboard_id}", summary="Delete dashboard")
def delete_dashboard(
    dashboard_id: str,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    _platform()
    try:
        ok = service.delete_dashboard(dashboard_id, organization_id)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    if not ok:
        raise HTTPException(404, "Dashboard not found")
    return {"deleted": True}


@router.post("/validate-widgets", summary="Validate widget definitions")
def validate_widgets(
    widgets: list[dict[str, Any]] = Body(...),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    _platform()
    try:
        service._validate_widgets(widgets)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"valid": True, "count": len(widgets)}
