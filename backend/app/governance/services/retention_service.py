"""Data retention policy service."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.governance.models.policy import RetentionPolicy

log = get_logger("governance.retention")


class RetentionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_policy(
        self, data: dict[str, Any], organization_id: str, created_by: str = ""
    ) -> RetentionPolicy:
        policy = RetentionPolicy(
            organization_id=organization_id,
            name=data["name"],
            resource_type=data["resource_type"],
            retention_days=data.get("retention_days", 365),
            auto_delete=data.get("auto_delete", False),
            created_by=created_by,
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        log.info(
            "retention_policy_created", policy_id=policy.id, resource_type=policy.resource_type
        )
        return policy

    def list_policies(self, organization_id: str) -> list[RetentionPolicy]:
        stmt = select(RetentionPolicy).where(RetentionPolicy.organization_id == organization_id)
        return list(self.db.scalars(stmt.all()))

    def get_expired_date(self, retention_days: int) -> datetime:
        return datetime.utcnow() - timedelta(days=retention_days)

    def check_retention(self, organization_id: str) -> dict[str, Any]:
        policies = self.list_policies(organization_id)
        results = []
        for p in policies:
            if p.auto_delete and not p.legal_hold:
                expired_date = self.get_expired_date(p.retention_days)
                results.append(
                    {
                        "resource_type": p.resource_type,
                        "retention_days": p.retention_days,
                        "expired_before": str(expired_date),
                        "legal_hold": p.legal_hold,
                    }
                )
        return {"policies": len(policies), "auto_delete_candidates": results}
