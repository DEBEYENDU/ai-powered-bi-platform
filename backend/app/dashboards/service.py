"""Dashboard service: CRUD over the Dashboard model + widget validation.

Widget ``kind`` values are validated against a fixed vocabulary; widget data
resolution stays in analytics/AI (referenced by id in ``config``).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.admin.repositories.db_store import db_available
from app.dashboards.models import Dashboard
from app.db.session import get_db_session

WIDGET_KINDS = {"kpi", "chart", "table", "text", "ai_insights", "forecast", "gauge"}


def _require_db() -> None:
    if not db_available():
        raise ValueError("Database is not available")


def _to_out(row: Dashboard) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description or "",
        "organization_id": row.organization_id,
        "widget_count": len(row.widgets or []),
        "shared": row.shared,
        "archived": row.archived,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _to_detail(row: Dashboard) -> dict[str, Any]:
    return {
        **_to_out(row),
        "layout": row.layout or {},
        "widgets": row.widgets or [],
        "filters": row.filters or {},
    }


def _validate_widgets(widgets: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for widget in widgets:
        wid = widget.get("widget_id", "")
        if not wid or wid in seen:
            raise ValueError("Each widget needs a unique widget_id")
        seen.add(wid)
        if widget.get("kind") not in WIDGET_KINDS:
            raise ValueError(f"Unknown widget kind: {widget.get('kind')!r}")


def create_dashboard(data: dict[str, Any], owner_id: str = "") -> dict[str, Any]:
    _require_db()
    _validate_widgets(data.get("widgets", []))
    with get_db_session() as session:
        row = Dashboard(
            id=str(uuid4()),
            organization_id=data.get("organization_id", ""),
            owner_id=owner_id,
            name=data["name"],
            description=data.get("description", ""),
            layout=data.get("layout", {}),
            widgets=data.get("widgets", []),
            filters=data.get("filters", {}),
            shared=bool(data.get("shared", False)),
        )
        session.add(row)
        session.flush()
        return _to_detail(row)


def get_dashboard(dashboard_id: str) -> dict[str, Any] | None:
    _require_db()
    with get_db_session() as session:
        row = session.get(Dashboard, dashboard_id)
        return _to_detail(row) if row and not row.archived else None


def list_dashboards(
    organization_id: str | None = None, include_archived: bool = False
) -> list[dict[str, Any]]:
    _require_db()
    with get_db_session() as session:
        stmt = select(Dashboard)
        if organization_id:
            stmt = stmt.where(Dashboard.organization_id == organization_id)
        if not include_archived:
            stmt = stmt.where(Dashboard.archived.is_(False))
        return [_to_out(r) for r in session.scalars(stmt).all()]


def update_dashboard(dashboard_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    _require_db()
    with get_db_session() as session:
        row = session.get(Dashboard, dashboard_id)
        if row is None:
            return None
        if "widgets" in patch and patch["widgets"] is not None:
            _validate_widgets(patch["widgets"])
            row.widgets = patch["widgets"]
        for key in ("name", "description", "layout", "filters", "shared"):
            if patch.get(key) is not None:
                setattr(row, key, patch[key])
        session.flush()
        return _to_detail(row)


def archive_dashboard(dashboard_id: str, archived: bool = True) -> dict[str, Any] | None:
    _require_db()
    with get_db_session() as session:
        row = session.get(Dashboard, dashboard_id)
        if row is None:
            return None
        row.archived = archived
        session.flush()
        return _to_detail(row)


def delete_dashboard(dashboard_id: str) -> bool:
    _require_db()
    with get_db_session() as session:
        row = session.get(Dashboard, dashboard_id)
        if row is None:
            return False
        session.delete(row)
        return True
