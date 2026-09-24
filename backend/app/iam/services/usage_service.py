"""Usage metering — record and query tenant resource consumption."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.iam.models.tenant import UsageRecord

log = get_logger(__name__)


class UsageService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(self, organization_id: str, resource_type: str, quantity: int = 1, user_id: str | None = None, request_id: str | None = None, source: str | None = None) -> None:
        rec = UsageRecord(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            resource_type=resource_type,
            quantity=quantity,
            user_id=user_id,
            request_id=request_id,
            source=source,
        )
        self.db.add(rec)
        self.db.commit()

    def get_usage(self, organization_id: str, resource_type: str, period_start: datetime | None = None) -> int:
        q = self.db.query(func.coalesce(func.sum(UsageRecord.quantity), 0)).filter(
            UsageRecord.organization_id == organization_id,
            UsageRecord.resource_type == resource_type,
        )
        if period_start:
            q = q.filter(UsageRecord.recorded_at >= period_start)
        return q.scalar() or 0

    def get_current_month_usage(self, organization_id: str, resource_type: str) -> int:
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return self.get_usage(organization_id, resource_type, month_start)

    def get_usage_summary(self, organization_id: str) -> dict[str, int]:
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        resources = ["users", "datasets", "storage_mb", "ai_requests", "ai_tokens", "queries", "reports", "dashboards", "workflows", "rag_documents", "rag_storage_mb", "predictions", "api_keys"]
        summary = {}
        for r in resources:
            summary[r] = self.get_usage(organization_id, r, month_start)
        return summary

    def get_usage_by_period(self, organization_id: str, days: int = 30) -> list[dict[str, Any]]:
        since = datetime.utcnow() - timedelta(days=days)
        records = (
            self.db.query(UsageRecord)
            .filter(UsageRecord.organization_id == organization_id, UsageRecord.recorded_at >= since)
            .order_by(UsageRecord.recorded_at.desc())
            .limit(1000)
            .all()
        )
        return [
            {"resource_type": r.resource_type, "quantity": r.quantity, "recorded_at": r.recorded_at.isoformat(), "user_id": r.user_id}
            for r in records
        ]
