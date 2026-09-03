"""In-memory repositories for reports (swap with SQLAlchemy impl when db lands).

Keeps the service layer persistence-agnostic: same interface works against
the SQLAlchemy models in ``models/report.py`` once ``app.db`` exists.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ReportRepository:
    def __init__(self) -> None:
        self._reports: Dict[str, Dict[str, Any]] = {}
        self._versions: Dict[str, List[Dict[str, Any]]] = {}

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        record = dict(data)
        record.setdefault("id", str(uuid4()))
        record.setdefault("status", "draft")
        record.setdefault("current_version", 0)
        record["created_at"] = record.get("created_at", datetime.utcnow().isoformat())
        record["updated_at"] = record["created_at"]
        self._reports[record["id"]] = record
        return record

    def get(self, report_id: str) -> Optional[Dict[str, Any]]:
        record = self._reports.get(report_id)
        return dict(record) if record else None

    def update(self, report_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        record = self._reports.get(report_id)
        if record is None:
            return None
        record.update(patch)
        record["updated_at"] = datetime.utcnow().isoformat()
        return dict(record)

    def delete(self, report_id: str) -> bool:
        record = self._reports.get(report_id)
        if record is None:
            return False
        record["deleted_at"] = datetime.utcnow().isoformat()
        record["status"] = "archived"
        return True

    def list(self, organization_id: Optional[str] = None, report_type: Optional[str] = None,
             status: Optional[str] = None, tags: Optional[List[str]] = None,
             search: str = "", limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        results = [r for r in self._reports.values() if not r.get("deleted_at")]
        if organization_id:
            results = [r for r in results if r.get("organization_id") == organization_id]
        if report_type:
            results = [r for r in results if r.get("report_type") == report_type]
        if status:
            results = [r for r in results if r.get("status") == status]
        if tags:
            results = [r for r in results if set(tags) & set(r.get("tags", []))]
        if search:
            q = search.lower()
            results = [r for r in results
                       if q in str(r.get("title", "")).lower() or q in str(r.get("description", "")).lower()]
        return [dict(r) for r in results[offset:offset + limit]]

    # -- versions (immutable snapshots) --
    def add_version(self, report_id: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        versions = self._versions.setdefault(report_id, [])
        version = dict(snapshot)
        version["version_number"] = len(versions) + 1
        version["created_at"] = datetime.utcnow().isoformat()
        versions.append(version)
        record = self._reports.get(report_id)
        if record:
            record["current_version"] = version["version_number"]
            record["updated_at"] = version["created_at"]
        return version

    def versions(self, report_id: str) -> List[Dict[str, Any]]:
        return [dict(v) for v in self._versions.get(report_id, [])]

    def compare(self, report_id: str, from_version: int, to_version: int) -> Dict[str, Any]:
        versions = {v["version_number"]: v for v in self._versions.get(report_id, [])}
        old = versions.get(from_version, {}).get("definition_snapshot", {}).get("sections", [])
        new = versions.get(to_version, {}).get("definition_snapshot", {}).get("sections", [])
        old_ids = {s.get("section_id") for s in old}
        new_ids = {s.get("section_id") for s in new}
        old_map = {s.get("section_id"): s for s in old}
        new_map = {s.get("section_id"): s for s in new}
        return {
            "from_version": from_version, "to_version": to_version,
            "added_sections": sorted(new_ids - old_ids),
            "removed_sections": sorted(old_ids - new_ids),
            "changed_sections": sorted(
                sid for sid in old_ids & new_ids if old_map[sid] != new_map[sid]),
        }
