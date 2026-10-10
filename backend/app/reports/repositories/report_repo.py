"""DB-backed repositories for the reports engine.

Swapped from the original in-memory dict (whose docstring said "swap with
SQLAlchemy impl when db lands"): reports now persist across requests, so
create → list/get/generate → delete all work, and every read can be scoped to
the caller's organization. The interface is unchanged — the service layer and
routers keep working.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.reports.models.report import ReportRecord, ReportVersionRecord


def _as_uuid(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _same_org(a: object, b: object) -> bool:
    ua, ub = _as_uuid(a), _as_uuid(b)
    return ua is not None and ua == ub


def _to_dict(record: ReportRecord) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "organization_id": str(record.organization_id),
        "owner_id": str(record.owner_id),
        "title": record.title,
        "description": record.description or "",
        "report_type": (
            record.report_type.value
            if hasattr(record.report_type, "value")
            else str(record.report_type)
        ),
        "status": (
            record.status.value
            if hasattr(record.status, "value")
            else str(record.status)
        ),
        "template_id": str(record.template_id) if record.template_id else None,
        "dataset_id": str(record.dataset_id) if record.dataset_id else None,
        "dashboard_id": str(record.dashboard_id) if record.dashboard_id else None,
        "definition": record.definition or {},
        "current_version": record.current_version or 0,
        "tags": record.tags or [],
        "created_at": record.created_at.isoformat() if record.created_at else "",
        "updated_at": record.updated_at.isoformat() if record.updated_at else "",
        "deleted_at": record.deleted_at.isoformat() if record.deleted_at else None,
    }


class ReportRepository:
    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Persist a report. The organization and owner are required: the
        ``reports`` table columns are NOT NULL UUIDs and every read is
        org-scoped."""
        org = _as_uuid(data.get("organization_id"))
        owner = _as_uuid(data.get("owner_id"))
        if org is None:
            raise ValueError("A valid organization_id is required to create a report")
        if owner is None:
            raise ValueError("A valid owner_id is required to create a report")

        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            record = ReportRecord(
                organization_id=org,
                owner_id=owner,
                title=data.get("title") or "Untitled report",
                description=data.get("description") or "",
                report_type=str(data.get("report_type") or "custom"),
                status="draft",
                template_id=_as_uuid(data.get("template_id")),
                dataset_id=_as_uuid(data.get("dataset_id")),
                dashboard_id=_as_uuid(data.get("dashboard_id")),
                definition=data.get("definition") or {},
                tags=data.get("tags") or [],
                current_version=0,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return _to_dict(record)
        finally:
            db.close()

    def get(
        self, report_id: str, organization_id: str | None = None
    ) -> dict[str, Any] | None:
        rid = _as_uuid(report_id)
        if rid is None:
            return None
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            record = db.get(ReportRecord, rid)
            if record is None or record.deleted_at is not None:
                return None
            if organization_id and not _same_org(record.organization_id, organization_id):
                return None
            return _to_dict(record)
        finally:
            db.close()

    def update(
        self,
        report_id: str,
        patch: dict[str, Any],
        organization_id: str | None = None,
    ) -> dict[str, Any] | None:
        rid = _as_uuid(report_id)
        if rid is None:
            return None
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            record = db.get(ReportRecord, rid)
            if record is None or record.deleted_at is not None:
                return None
            if organization_id and not _same_org(record.organization_id, organization_id):
                return None
            for key in ("title", "description", "definition", "tags", "status"):
                if key in patch and patch[key] is not None:
                    setattr(record, key, patch[key])
            db.commit()
            db.refresh(record)
            return _to_dict(record)
        finally:
            db.close()

    def delete(self, report_id: str, organization_id: str | None = None) -> bool:
        rid = _as_uuid(report_id)
        if rid is None:
            return False
        from datetime import datetime

        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            record = db.get(ReportRecord, rid)
            if record is None or record.deleted_at is not None:
                return False
            if organization_id and not _same_org(record.organization_id, organization_id):
                return False
            record.deleted_at = datetime.utcnow()  # soft delete
            db.commit()
            return True
        finally:
            db.close()

    def list(
        self,
        organization_id: str | None = None,
        report_type: str | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
        search: str = "",
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            stmt = (
                select(ReportRecord)
                .where(ReportRecord.deleted_at.is_(None))
                .order_by(ReportRecord.created_at.desc())
            )
            if organization_id:
                org = _as_uuid(organization_id)
                if org is not None:
                    stmt = stmt.where(ReportRecord.organization_id == org)
            if report_type:
                stmt = stmt.where(ReportRecord.report_type == report_type)
            if status:
                stmt = stmt.where(ReportRecord.status == status)
            if search:
                stmt = stmt.where(
                    ReportRecord.title.ilike(f"%{search}%")
                    | ReportRecord.description.ilike(f"%{search}%")
                )
            stmt = stmt.offset(offset).limit(limit)
            results = [_to_dict(r) for r in db.scalars(stmt).all()]
            if tags:
                results = [r for r in results if set(tags) & set(r.get("tags", []))]
            return results
        finally:
            db.close()

    # -- versions (immutable snapshots) --
    def add_version(self, report_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        rid = _as_uuid(report_id)
        if rid is None:
            raise ValueError(f"Invalid report id: {report_id!r}")
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            record = db.get(ReportRecord, rid)
            if record is None:
                raise ValueError(f"Report '{report_id}' not found")
            current = db.scalar(
                select(ReportRecord.current_version).where(ReportRecord.id == rid)
            )
            version = ReportVersionRecord(
                report_id=rid,
                version_number=(current or 0) + 1,
                definition_snapshot=snapshot.get("definition_snapshot", {}),
                rendered_formats=snapshot.get("formats", snapshot.get("rendered_formats", [])),
            )
            db.add(version)
            record.current_version = version.version_number
            db.commit()
            db.refresh(version)
            return {
                "id": str(version.id),
                "report_id": str(version.report_id),
                "version_number": version.version_number,
                "created_at": version.created_at.isoformat() if version.created_at else "",
                "definition_snapshot": version.definition_snapshot or {},
                "formats": version.rendered_formats or [],
            }
        finally:
            db.close()

    def versions(self, report_id: str) -> list[dict[str, Any]]:
        rid = _as_uuid(report_id)
        if rid is None:
            return []
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            stmt = (
                select(ReportVersionRecord)
                .where(ReportVersionRecord.report_id == rid)
                .order_by(ReportVersionRecord.version_number)
            )
            return [
                {
                    "id": str(v.id),
                    "report_id": str(v.report_id),
                    "version_number": v.version_number,
                    "created_at": v.created_at.isoformat() if v.created_at else "",
                    "definition_snapshot": v.definition_snapshot or {},
                    "formats": v.rendered_formats or [],
                }
                for v in db.scalars(stmt).all()
            ]
        finally:
            db.close()

    def compare(self, report_id: str, from_version: int, to_version: int) -> dict[str, Any]:
        versions = {v["version_number"]: v for v in self.versions(report_id)}
        old = versions.get(from_version, {}).get("definition_snapshot", {}).get("sections", [])
        new = versions.get(to_version, {}).get("definition_snapshot", {}).get("sections", [])
        old_ids = {s.get("section_id") for s in old}
        new_ids = {s.get("section_id") for s in new}
        old_map = {s.get("section_id"): s for s in old}
        new_map = {s.get("section_id"): s for s in new}
        return {
            "from_version": from_version,
            "to_version": to_version,
            "added_sections": sorted(new_ids - old_ids),
            "removed_sections": sorted(old_ids - new_ids),
            "changed_sections": sorted(
                sid for sid in old_ids & new_ids if old_map[sid] != new_map[sid]
            ),
        }
