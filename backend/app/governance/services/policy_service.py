"""Policy management service — CRUD for governance policies."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.governance.models.policy import GovernancePolicy

log = get_logger("governance.policy")


class PolicyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_policy(
        self, data: dict[str, Any], organization_id: str, created_by: str = ""
    ) -> GovernancePolicy:
        policy = GovernancePolicy(
            organization_id=organization_id,
            name=data["name"],
            description=data.get("description", ""),
            resource=data["resource"],
            action=data["action"],
            subject_type=data.get("subject_type", "role"),
            subject_id=data.get("subject_id", ""),
            effect=data.get("effect", "ALLOW"),
            conditions=data.get("conditions", {}),
            priority=data.get("priority", 0),
            created_by=created_by,
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        log.info("policy_created", policy_id=policy.id, name=policy.name)
        return policy

    def get_policy(self, policy_id: str, organization_id: str) -> GovernancePolicy | None:
        stmt = select(GovernancePolicy).where(
            GovernancePolicy.id == policy_id,
            GovernancePolicy.organization_id == organization_id,
        )
        return self.db.scalars(stmt).first()

    def list_policies(
        self, organization_id: str, resource: str | None = None
    ) -> list[GovernancePolicy]:
        stmt = select(GovernancePolicy).where(GovernancePolicy.organization_id == organization_id)
        if resource:
            stmt = stmt.where(GovernancePolicy.resource == resource)
        return list(self.db.scalars(stmt.order_by(GovernancePolicy.priority.desc()).all()))

    def update_policy(
        self, policy_id: str, organization_id: str, data: dict[str, Any]
    ) -> GovernancePolicy | None:
        policy = self.get_policy(policy_id, organization_id)
        if not policy:
            return None
        for key, value in data.items():
            if hasattr(policy, key) and value is not None:
                setattr(policy, key, value)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def delete_policy(self, policy_id: str, organization_id: str) -> bool:
        policy = self.get_policy(policy_id, organization_id)
        if not policy:
            return False
        self.db.delete(policy)
        self.db.commit()
        return True

    def toggle_policy(self, policy_id: str, organization_id: str) -> GovernancePolicy | None:
        policy = self.get_policy(policy_id, organization_id)
        if not policy:
            return None
        policy.enabled = not policy.enabled
        self.db.commit()
        self.db.refresh(policy)
        return policy
