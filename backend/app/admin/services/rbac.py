"""RBAC service: system/org/custom roles, permission matrix, simulator.

Permission model: granular ``resource.action`` codes (e.g. ``users.delete``).
Resources: users, organizations, roles, dashboards, reports, datasets, ai,
pipelines, settings, alerts, metrics, audit, jobs.
Actions per resource: view, create, update, delete, execute, export (subset
where applicable).

Backward compatibility: legacy ``resource:action`` codes (users:read,
datasets:write, ai:use, ...) granted by older clients or referenced by the
tool registry are expanded through ``LEGACY_ALIASES`` at check time, so old
grants keep working without migration.

Persistence mirrors other admin services: PostgreSQL via ``db_store`` when
reachable, in-memory otherwise.
"""

from __future__ import annotations

import contextlib
from typing import Any
from uuid import uuid4

from app.admin.models.admin import SystemRoles
from app.admin.repositories import db_store

# resource -> allowed actions
RESOURCE_ACTIONS: dict[str, list[str]] = {
    "users": ["view", "create", "update", "delete", "export"],
    "organizations": ["view", "create", "update", "delete"],
    "roles": ["view", "create", "update", "delete", "assign"],
    "dashboards": ["view", "create", "update", "delete", "export"],
    "reports": ["view", "create", "update", "delete", "export", "execute"],
    "datasets": ["view", "create", "update", "delete", "export"],
    "ai": ["view", "execute"],
    "pipelines": ["view", "create", "execute", "delete"],
    "settings": ["view", "update"],
    "alerts": ["view", "create", "update", "delete", "execute"],
    "metrics": ["view", "export"],
    "audit": ["view", "export"],
    "jobs": ["view", "execute", "delete"],
    "knowledge": ["view", "upload", "update", "delete", "search", "manage"],
}

# Legacy "resource:action" codes expand to these canonical grants.
LEGACY_ALIASES: dict[str, set[str]] = {
    "users:read": {"users.view"},
    "users:write": {"users.create", "users.update"},
    "users:suspend": {"users.update"},
    "orgs:read": {"organizations.view"},
    "orgs:write": {"organizations.create", "organizations.update"},
    "orgs:suspend": {"organizations.update"},
    "roles:manage": {"roles.view", "roles.create", "roles.update", "roles.delete", "roles.assign"},
    "datasets:read": {"datasets.view"},
    "datasets:write": {"datasets.create", "datasets.update"},
    "etl:run": {"pipelines.execute"},
    "analytics:read": {"metrics.view"},
    "dashboards:read": {"dashboards.view"},
    "dashboards:write": {"dashboards.create", "dashboards.update"},
    "reports:read": {"reports.view"},
    "reports:write": {"reports.create", "reports.update"},
    "ai:use": {"ai.view", "ai.execute"},
    "ml:use": {"ai.execute"},
    "admin:settings": {"settings.view", "settings.update"},
    "admin:flags": {"settings.view", "settings.update"},
    "admin:alerts": {"alerts.view", "alerts.update"},
    "knowledge:read": {"knowledge.view"},
    "knowledge:upload": {"knowledge.upload"},
    "knowledge:write": {"knowledge.update", "knowledge.upload"},
    "knowledge:search": {"knowledge.search"},
    "knowledge:manage": {
        "knowledge.view",
        "knowledge.upload",
        "knowledge.update",
        "knowledge.delete",
        "knowledge.search",
        "knowledge.manage",
    },
}


def _all_codes() -> dict[str, dict[str, str]]:
    catalog: dict[str, dict[str, str]] = {}
    for resource, actions in RESOURCE_ACTIONS.items():
        for action in actions:
            code = f"{resource}.{action}"
            catalog[code] = {
                "code": code,
                "group": resource,
                "description": f"Can {action} {resource}",
            }
    return catalog


class RBACService:
    def __init__(self) -> None:
        self._permissions: dict[str, dict[str, Any]] = _all_codes()
        self._roles: dict[str, dict[str, Any]] = {}
        self._role_permissions: dict[str, set[str]] = {}
        self._user_roles: dict[str, set[str]] = {}
        self._seed()
        self._persist_catalog()

    def _persist_catalog(self) -> None:
        with contextlib.suppress(Exception):
            for code, perm in self._permissions.items():
                db_store.permission_ensure(code, perm["group"], perm["description"])

    def _persist_role(self, role_id: str) -> None:
        with contextlib.suppress(Exception):
            role = self._roles[role_id]
            db_store.role_upsert(
                role_id,
                {
                    "name": role["name"],
                    "description": role.get("description", ""),
                    "organization_id": role.get("organization_id"),
                    "system_role": role.get("system_role", False),
                },
                sorted(self._role_permissions.get(role_id, set())),
            )

    def _seed(self) -> None:
        def _all() -> list[str]:
            return list(self._permissions)

        def _views() -> list[str]:
            return [c for c in self._permissions if c.endswith(".view")]

        role_grants: dict[str, list[str]] = {
            SystemRoles.SUPERADMIN: _all(),
            SystemRoles.ORG_ADMIN: [
                c
                for c in self._permissions
                if not (c.startswith("settings.") and c != "settings.view")
            ],
            SystemRoles.ANALYST: [
                "datasets.view",
                "datasets.create",
                "datasets.update",
                "dashboards.view",
                "dashboards.create",
                "dashboards.update",
                "reports.view",
                "reports.create",
                "ai.view",
                "ai.execute",
                "pipelines.view",
                "pipelines.execute",
                "metrics.view",
                "jobs.view",
            ],
            SystemRoles.VIEWER: _views(),
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
    def normalize_codes(self, codes: list[str]) -> set[str]:
        """Expand legacy codes to canonical grants; reject unknown codes."""
        normalized: set[str] = set()
        unknown: list[str] = []
        for code in codes:
            if code in self._permissions:
                normalized.add(code)
            elif code in LEGACY_ALIASES:
                normalized |= LEGACY_ALIASES[code]
            else:
                unknown.append(code)
        if unknown:
            raise ValueError(f"Unknown permissions: {unknown}")
        return normalized

    def create_role(
        self,
        name: str,
        description: str = "",
        organization_id: str | None = None,
        permission_codes: list[str] | None = None,
    ) -> dict[str, Any]:
        rid = str(uuid4())
        grants = self.normalize_codes(permission_codes or [])
        self._roles[rid] = {
            "id": rid,
            "name": name,
            "description": description,
            "system_role": False,
            "organization_id": organization_id,
        }
        self._role_permissions[rid] = grants
        self._persist_role(rid)
        return self._roles[rid]

    def update_role(self, role_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        role = self._roles.get(role_id)
        if role is None:
            return None
        if role.get("system_role"):
            raise ValueError("System roles cannot be edited")
        for key in ("name", "description", "organization_id"):
            if key in patch:
                role[key] = patch[key]
        if "permission_codes" in patch:
            self._role_permissions[role_id] = self.normalize_codes(patch["permission_codes"])
        self._persist_role(role_id)
        return role

    def clone_role(self, role_id: str, name: str) -> dict[str, Any]:
        source = self._roles.get(role_id)
        if source is None:
            raise ValueError("Role not found")
        return self.create_role(
            name=name,
            description=f"Clone of {source['name']}",
            organization_id=source.get("organization_id"),
            permission_codes=sorted(self._role_permissions.get(role_id, set())),
        )

    def delete_role(self, role_id: str) -> bool:
        role = self._roles.get(role_id)
        if role is None:
            return False
        if role.get("system_role"):
            raise ValueError("System roles cannot be deleted")
        del self._roles[role_id]
        self._role_permissions.pop(role_id, None)
        for assigned in self._user_roles.values():
            assigned.discard(role_id)
        with contextlib.suppress(Exception):
            db_store.role_delete_db(role_id)
        return True

    def list_roles(self) -> list[dict[str, Any]]:
        return list(self._roles.values())

    def get_role(self, role_id: str) -> dict[str, Any] | None:
        role = self._roles.get(role_id)
        if role is None:
            return None
        return {**role, "permission_codes": sorted(self._role_permissions.get(role_id, set()))}

    def role_users(self, role_id: str) -> list[str]:
        if role_id not in self._roles:
            raise ValueError("Role not found")
        return sorted(uid for uid, roles in self._user_roles.items() if role_id in roles)

    def grant_permission(self, role_id: str, code: str) -> None:
        if role_id not in self._roles:
            raise ValueError("Role not found")
        self._role_permissions.setdefault(role_id, set()).update(self.normalize_codes([code]))
        self._persist_role(role_id)

    def revoke_permission(self, role_id: str, code: str) -> bool:
        grants = self._role_permissions.get(role_id, set())
        if self._roles.get(role_id, {}).get("system_role"):
            raise ValueError("System roles cannot be edited")
        if code in grants:
            grants.discard(code)
            self._persist_role(role_id)
            return True
        return False

    def assign_role(self, user_id: str, role_id: str) -> None:
        if role_id not in self._roles:
            raise ValueError("Role not found")
        self._user_roles.setdefault(user_id, set()).add(role_id)
        with contextlib.suppress(Exception):
            db_store.user_role_grant(user_id, role_id, None)

    def unassign_role(self, user_id: str, role_id: str) -> bool:
        roles = self._user_roles.get(user_id, set())
        if role_id in roles:
            roles.discard(role_id)
            with contextlib.suppress(Exception):
                db_store.user_role_revoke_db(user_id, role_id)
            return True
        return False

    def user_roles(self, user_id: str) -> list[dict[str, Any]]:
        return [
            self._roles[rid] for rid in self._user_roles.get(user_id, set()) if rid in self._roles
        ]

    # -- evaluation --
    def effective_permissions(self, user_id: str) -> set[str]:
        granted: set[str] = set()
        for rid in self._user_roles.get(user_id, set()):
            granted |= self._role_permissions.get(rid, set())
        return granted

    def check(self, user_id: str, permission: str) -> bool:
        wanted = LEGACY_ALIASES.get(permission, {permission})
        return bool(wanted & self.effective_permissions(user_id))

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

    def permission_matrix(self) -> dict[str, Any]:
        """Full resource-by-action matrix for the RBAC UI."""
        return {
            "resources": RESOURCE_ACTIONS,
            "legacy_aliases": {k: sorted(v) for k, v in LEGACY_ALIASES.items()},
        }
