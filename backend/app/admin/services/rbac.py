"""RBAC service: system/org/custom roles, permission groups, simulator.

Seeds ``DEFAULT_PERMISSIONS`` plus four system roles. ``check`` evaluates
user → roles → permissions. ``simulate`` previews effective permissions.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.admin.models.admin import DEFAULT_PERMISSIONS, SystemRoles


class RBACService:
    def __init__(self) -> None:
        self._permissions: dict[str, dict[str, Any]] = {}
        self._roles: dict[str, dict[str, Any]] = {}
        self._role_permissions: dict[str, set[str]] = {}
        self._user_roles: dict[str, set[str]] = {}
        self._seed()

    def _seed(self) -> None:
        for code, group, desc in DEFAULT_PERMISSIONS:
            self._permissions[code] = {"code": code, "group": group, "description": desc}
        role_grants: dict[str, list[str]] = {
            SystemRoles.SUPERADMIN: list(self._permissions),
            SystemRoles.ORG_ADMIN: [c for c in self._permissions if not c.startswith("admin:")]
            + ["admin:alerts"],
            SystemRoles.ANALYST: [
                "datasets:read",
                "datasets:write",
                "etl:run",
                "analytics:read",
                "dashboards:read",
                "dashboards:write",
                "reports:read",
                "reports:write",
                "ai:use",
                "ml:use",
            ],
            SystemRoles.VIEWER: [
                "datasets:read",
                "analytics:read",
                "dashboards:read",
                "reports:read",
                "ai:use",
            ],
        }
        for name, grants in role_grants.items():
            rid = f"sys-{name}"
            self._roles[rid] = {
                "id": rid,
                "name": name,
                "system_role": True,
                "organization_id": None,
                "description": f"System role {name}",
            }
            self._role_permissions[rid] = set(grants)

    # -- roles --
    def create_role(
        self,
        name: str,
        description: str = "",
        organization_id: str | None = None,
        permission_codes: list[str] | None = None,
    ) -> dict[str, Any]:
        rid = str(uuid4())
        unknown = [c for c in (permission_codes or []) if c not in self._permissions]
        if unknown:
            raise ValueError(f"Unknown permissions: {unknown}")
        self._roles[rid] = {
            "id": rid,
            "name": name,
            "description": description,
            "system_role": False,
            "organization_id": organization_id,
        }
        self._role_permissions[rid] = set(permission_codes or [])
        return self._roles[rid]

    def list_roles(self) -> list[dict[str, Any]]:
        return list(self._roles.values())

    def grant_permission(self, role_id: str, code: str) -> None:
        if role_id not in self._roles:
            raise ValueError("Role not found")
        if code not in self._permissions:
            raise ValueError("Permission not found")
        self._role_permissions.setdefault(role_id, set()).add(code)

    def assign_role(self, user_id: str, role_id: str) -> None:
        if role_id not in self._roles:
            raise ValueError("Role not found")
        self._user_roles.setdefault(user_id, set()).add(role_id)

    def unassign_role(self, user_id: str, role_id: str) -> bool:
        roles = self._user_roles.get(user_id, set())
        if role_id in roles:
            roles.discard(role_id)
            return True
        return False

    # -- evaluation --
    def effective_permissions(self, user_id: str) -> set[str]:
        granted: set[str] = set()
        for rid in self._user_roles.get(user_id, set()):
            granted |= self._role_permissions.get(rid, set())
        return granted

    def check(self, user_id: str, permission: str) -> bool:
        return permission in self.effective_permissions(user_id)

    def simulate(self, user_id: str) -> dict[str, Any]:
        perms = sorted(self.effective_permissions(user_id))
        groups: dict[str, list[str]] = {}
        for code in perms:
            groups.setdefault(self._permissions[code]["group"], []).append(code)
        return {
            "user_id": user_id,
            "permissions": perms,
            "by_group": groups,
            "roles": sorted(self._user_roles.get(user_id, set())),
        }

    def permission_groups(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        for code, perm in self._permissions.items():
            groups.setdefault(perm["group"], []).append(code)
        return groups
