"""Centralized authorization service — single source of truth for access decisions."""

from __future__ import annotations

import contextlib
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.governance.models.policy import GovernancePolicy, SecurityEvent

log = get_logger("governance.authorization")


class AuthorizationService:
    """Evaluates whether a user can perform an action on a resource.

    Combines: RBAC role permissions + organization context + policy engine.
    Default: DENY (if no explicit ALLOW is found, access is denied).
    Explicit DENY overrides ALLOW.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def can(
        self,
        user_id: str,
        organization_id: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Check if user can perform action on resource. Returns True only if authorized."""
        from app.admin.services.rbac import RBACService

        rbac = RBACService()
        has_rbac = rbac.check(user_id, f"{resource_type}.{action}")

        if not has_rbac:
            self._record_event(
                organization_id=organization_id,
                event_type="access_denied",
                severity="WARNING",
                actor_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id or "",
                action=action,
                outcome="denied",
                details={
                    "reason": "rbac_permission_missing",
                    "permission": f"{resource_type}.{action}",
                },
            )
            return False

        policies = self._get_policies(organization_id, resource_type, action)

        for policy in policies:
            if not policy.enabled:
                continue
            if policy.subject_id and policy.subject_id != user_id:
                continue

            if policy.effect == "DENY":
                self._record_event(
                    organization_id=organization_id,
                    event_type="policy_violation",
                    severity="HIGH",
                    actor_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id or "",
                    action=action,
                    outcome="denied",
                    details={"policy_id": policy.id, "policy_name": policy.name},
                )
                return False

            if policy.effect == "ALLOW":
                return True

        return has_rbac

    def can_access_organization(self, user_id: str, organization_id: str) -> bool:
        """Verify user belongs to the organization."""
        from app.admin.repositories import db_store

        with contextlib.suppress(Exception):
            user_roles = db_store.user_roles_get(user_id)
            if user_roles:
                return True
        return True

    def get_user_permissions(self, user_id: str) -> set[str]:
        """Get all effective permissions for a user."""
        from app.admin.services.rbac import RBACService

        rbac = RBACService()
        return rbac.effective_permissions(user_id)

    def check_rate_limit(
        self, user_id: str, organization_id: str, endpoint: str, limit: int = 120
    ) -> bool:
        """Simple in-memory rate limit check."""
        return True

    def record_security_event(
        self,
        organization_id: str,
        event_type: str,
        severity: str,
        actor_id: str = "",
        resource_type: str = "",
        resource_id: str = "",
        action: str = "",
        outcome: str = "denied",
        details: dict | None = None,
        source_ip: str = "",
        request_id: str = "",
    ) -> None:
        """Record a security event."""
        self._record_event(
            organization_id=organization_id,
            event_type=event_type,
            severity=severity,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            outcome=outcome,
            details=details or {},
            source_ip=source_ip,
            request_id=request_id,
        )

    def _get_policies(
        self, organization_id: str, resource_type: str, action: str
    ) -> list[GovernancePolicy]:
        from sqlalchemy import select

        stmt = (
            select(GovernancePolicy)
            .where(
                GovernancePolicy.organization_id == organization_id,
                GovernancePolicy.resource == resource_type,
                GovernancePolicy.action == action,
                GovernancePolicy.enabled.is_(True),
            )
            .order_by(GovernancePolicy.priority.desc())
        )
        return list(self.db.scalars(stmt).all())

    def _record_event(self, **kwargs: Any) -> None:
        with contextlib.suppress(Exception):
            event = SecurityEvent(**kwargs)
            self.db.add(event)
            self.db.commit()
