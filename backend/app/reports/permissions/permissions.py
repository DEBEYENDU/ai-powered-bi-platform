"""Report permissions (RBAC).

Roles: owner > editor > reviewer > viewer. Organization/department grants and
per-report shares are evaluated in code until the roles/permissions tables
(Phase 4) land; this module is the single enforcement point the service and
routers call.
"""

from __future__ import annotations

ROLE_RANK = {"viewer": 1, "reviewer": 2, "editor": 3, "owner": 4}


class PermissionChecker:
    def __init__(self) -> None:
        # report_id -> list of {granted_to, role, can_export, can_distribute}
        self._shares: dict[str, list[dict[str, object]]] = {}

    def grant(
        self,
        report_id: str,
        granted_to: str,
        role: str = "viewer",
        can_export: bool = True,
        can_distribute: bool = False,
    ) -> dict[str, object]:
        if role not in ROLE_RANK:
            raise ValueError(f"Unknown role '{role}'")
        grant = {
            "granted_to": granted_to,
            "role": role,
            "can_export": can_export,
            "can_distribute": can_distribute,
        }
        self._shares.setdefault(report_id, []).append(grant)
        return grant

    def revoke(self, report_id: str, granted_to: str) -> bool:
        grants = self._shares.get(report_id, [])
        kept = [g for g in grants if g.get("granted_to") != granted_to]
        self._shares[report_id] = kept
        return len(kept) != len(grants)

    def role_of(
        self,
        report_id: str,
        user_id: str,
        owner_id: str | None = None,
        user_roles: list[str] | None = None,
        department: str | None = None,
    ) -> str | None:
        if owner_id and user_id == owner_id:
            return "owner"
        best: str | None = None
        candidates = [user_id, "org", *(user_roles or [])]
        if department:
            candidates.append(f"dept:{department}")
        for grant in self._shares.get(report_id, []):
            if str(grant.get("granted_to")) in candidates:
                role = str(grant.get("role"))
                if best is None or ROLE_RANK[role] > ROLE_RANK[best]:
                    best = role
        return best

    def require(
        self,
        report_id: str,
        action: str,
        user_id: str,
        owner_id: str | None = None,
        user_roles: list[str] | None = None,
        department: str | None = None,
    ) -> str:
        minimum = {
            "view": "viewer",
            "edit": "editor",
            "review": "reviewer",
            "approve": "editor",
            "export": "viewer",
            "distribute": "editor",
            "share": "editor",
            "delete": "owner",
        }.get(action, "viewer")
        role = self.role_of(report_id, user_id, owner_id, user_roles, department)
        if role is None or ROLE_RANK[role] < ROLE_RANK[minimum]:
            raise PermissionError(f"User '{user_id}' lacks '{action}' on report '{report_id}'")
        if action == "export":
            grants = [
                g
                for g in self._shares.get(report_id, [])
                if str(g.get("granted_to")) in [user_id, "org"]
            ]
            if grants and not any(g.get("can_export", True) for g in grants) and role != "owner":
                raise PermissionError("Export not allowed for this share")
        if action == "distribute":
            grants = [
                g
                for g in self._shares.get(report_id, [])
                if str(g.get("granted_to")) in [user_id, "org"]
            ]
            if (
                grants
                and not any(g.get("can_distribute", False) for g in grants)
                and role != "owner"
            ):
                raise PermissionError("Distribution not allowed for this share")
        return role
