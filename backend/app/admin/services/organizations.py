"""Organization administration: lifecycle, quotas, limits, branding.

Persistence mirrors the user service: PostgreSQL via ``db_store`` when
reachable (source of truth), in-memory mirror otherwise. Supports owner
assignment and archival (soft delete).
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.admin.repositories import db_store


class OrganizationAdminService:
    def __init__(self) -> None:
        self._orgs: dict[str, dict[str, Any]] = {}
        self._quotas: dict[str, dict[str, Any]] = {}
        self._settings: dict[str, dict[str, Any]] = {}

    def _merged(self) -> dict[str, dict[str, Any]]:
        merged = dict(self._orgs)
        rows = None
        with contextlib.suppress(Exception):
            rows = db_store.org_list_db()

        if rows:
            for row in rows:
                oid = row["id"]
                merged[oid] = {
                    **merged.get(oid, {}),
                    **{k: v for k, v in row.items() if v is not None},
                }
        return merged

    def create(self, name: str, slug: str = "", owner_id: str = "") -> dict[str, Any]:
        slug = slug or name.lower().replace(" ", "-")
        if not slug or len(slug) < 2:
            raise ValueError("Slug must be at least 2 characters")
        if any(o["slug"] == slug for o in self._merged().values()):
            raise ValueError(f"Organization with slug '{slug}' already exists")
        oid = str(uuid4())
        org = {
            "id": oid,
            "name": name,
            "slug": slug,
            "owner_id": owner_id or None,
            "suspended": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._orgs[oid] = org
        self._quotas[oid] = {
            "organization_id": oid,
            "storage_mb": 10240,
            "dataset_limit": 100,
            "ai_requests_per_day": 1000,
            "api_requests_per_minute": 120,
            "suspended": False,
        }
        self._settings[oid] = {"branding": {}, "subscription": "trial", "billing": {}}
        with contextlib.suppress(Exception):
            db_store.org_upsert(org)
            db_store.quota_upsert(self._quotas[oid])
        return org

    def get(self, org_id: str) -> dict[str, Any] | None:
        return self._merged().get(org_id)

    def update(self, org_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        org = self._merged().get(org_id)
        if org is None:
            return None
        if patch.get("slug"):
            for o in self._merged().values():
                if o["slug"] == patch["slug"] and o["id"] != org_id:
                    raise ValueError(f"Organization with slug '{patch['slug']}' already exists")
        for key in ("name", "slug", "owner_id"):
            if key in patch:
                org[key] = patch[key]
        self._orgs[org_id] = org
        with contextlib.suppress(Exception):
            db_store.org_upsert(org)
        return org

    def suspend(self, org_id: str, suspended: bool = True) -> dict[str, Any] | None:
        org = self._merged().get(org_id)
        if org is None:
            return None
        org["suspended"] = suspended
        self._orgs[org_id] = org
        quota = self._quotas.get(org_id)
        if quota is not None:
            quota["suspended"] = suspended
        with contextlib.suppress(Exception):
            db_store.org_upsert(org)
            if quota is not None:
                db_store.quota_upsert(quota)
        return org

    def delete(self, org_id: str) -> bool:
        """Archive (soft delete) an organization."""
        org = self._merged().get(org_id)
        if org is None:
            return False
        org["suspended"] = True
        org["deleted"] = True
        org["deleted_at"] = datetime.utcnow().isoformat()
        self._orgs[org_id] = org
        with contextlib.suppress(Exception):
            db_store.org_upsert(org)
        return True

    def restore(self, org_id: str) -> dict[str, Any] | None:
        org = self._merged().get(org_id)
        if org is None:
            return None
        org.pop("deleted", None)
        org.pop("deleted_at", None)
        org["suspended"] = False
        self._orgs[org_id] = org
        with contextlib.suppress(Exception):
            db_store.org_upsert(org)
        return org

    def list(self, include_archived: bool = False) -> list[dict[str, Any]]:
        orgs = [o for o in self._merged().values() if include_archived or not o.get("deleted")]
        return orgs

    def quotas(self, org_id: str) -> dict[str, Any] | None:
        return self._quotas.get(org_id)

    def update_quotas(self, org_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        quota = self._quotas.get(org_id)
        if quota is None:
            return None
        for key in (
            "storage_mb",
            "dataset_limit",
            "ai_requests_per_day",
            "api_requests_per_minute",
        ):
            if patch.get(key) is not None:
                if not isinstance(patch[key], int) or patch[key] < 0:
                    raise ValueError(f"Invalid quota '{key}'")
                quota[key] = patch[key]
        with contextlib.suppress(Exception):
            db_store.quota_upsert(quota)
        return quota

    def org_settings(self, org_id: str) -> dict[str, Any]:
        return self._settings.setdefault(
            org_id, {"branding": {}, "subscription": "trial", "billing": {}}
        )

    def update_org_settings(self, org_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        settings = self.org_settings(org_id)
        settings.update(patch)
        return settings
