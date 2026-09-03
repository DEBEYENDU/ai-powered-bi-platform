"""Organization administration: lifecycle, quotas, limits, branding."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


class OrganizationAdminService:
    def __init__(self) -> None:
        self._orgs: Dict[str, Dict[str, Any]] = {}
        self._quotas: Dict[str, Dict[str, Any]] = {}
        self._settings: Dict[str, Dict[str, Any]] = {}

    def create(self, name: str, slug: str = "") -> Dict[str, Any]:
        slug = slug or name.lower().replace(" ", "-")
        if any(o["slug"] == slug for o in self._orgs.values()):
            raise ValueError("Slug already exists")
        oid = str(uuid4())
        org = {"id": oid, "name": name, "slug": slug, "suspended": False,
               "created_at": datetime.utcnow().isoformat()}
        self._orgs[oid] = org
        self._quotas[oid] = {"organization_id": oid, "storage_mb": 10240,
                             "dataset_limit": 100, "ai_requests_per_day": 1000,
                             "api_requests_per_minute": 120, "suspended": False}
        self._settings[oid] = {"branding": {}, "subscription": "trial", "billing": {}}
        return org

    def get(self, org_id: str) -> Optional[Dict[str, Any]]:
        return self._orgs.get(org_id)

    def update(self, org_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        org = self._orgs.get(org_id)
        if org is None:
            return None
        for key in ("name", "slug"):
            if key in patch:
                org[key] = patch[key]
        return org

    def suspend(self, org_id: str, suspended: bool = True) -> Optional[Dict[str, Any]]:
        org = self._orgs.get(org_id)
        if org is None:
            return None
        org["suspended"] = suspended
        self._quotas.get(org_id, {})["suspended"] = suspended
        return org

    def delete(self, org_id: str) -> bool:
        org = self._orgs.get(org_id)
        if org is None:
            return False
        org["suspended"] = True
        org["deleted"] = True
        return True

    def restore(self, org_id: str) -> Optional[Dict[str, Any]]:
        org = self._orgs.get(org_id)
        if org is None:
            return None
        org.pop("deleted", None)
        org["suspended"] = False
        return org

    def list(self) -> List[Dict[str, Any]]:
        return [o for o in self._orgs.values() if not o.get("deleted")]

    def quotas(self, org_id: str) -> Optional[Dict[str, Any]]:
        return self._quotas.get(org_id)

    def update_quotas(self, org_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        quota = self._quotas.get(org_id)
        if quota is None:
            return None
        for key in ("storage_mb", "dataset_limit", "ai_requests_per_day",
                    "api_requests_per_minute"):
            if patch.get(key) is not None:
                if not isinstance(patch[key], int) or patch[key] < 0:
                    raise ValueError(f"Invalid quota '{key}'")
                quota[key] = patch[key]
        return quota

    def org_settings(self, org_id: str) -> Dict[str, Any]:
        return self._settings.setdefault(
            org_id, {"branding": {}, "subscription": "trial", "billing": {}})

    def update_org_settings(self, org_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        settings = self.org_settings(org_id)
        settings.update(patch)
        return settings
