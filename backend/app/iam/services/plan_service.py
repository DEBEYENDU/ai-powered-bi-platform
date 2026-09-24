"""Plan management service — CRUD for billing plans with default seed data."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.iam.models.tenant import Plan

log = get_logger(__name__)

DEFAULT_PLANS = [
    {"name": "free", "display_name": "Free", "max_users": 3, "max_datasets": 5, "max_storage_mb": 100, "max_ai_requests": 50, "max_ai_tokens": 10000, "max_workflows": 2, "max_reports": 5, "max_dashboards": 5, "max_rag_documents": 20, "max_rag_storage_mb": 50, "max_predictions": 10, "max_api_keys": 2, "max_queries_per_minute": 30, "max_concurrent_queries": 2},
    {"name": "starter", "display_name": "Starter", "max_users": 10, "max_datasets": 25, "max_storage_mb": 1000, "max_ai_requests": 200, "max_ai_tokens": 100000, "max_workflows": 10, "max_reports": 25, "max_dashboards": 20, "max_rag_documents": 100, "max_rag_storage_mb": 500, "max_predictions": 50, "max_api_keys": 5, "max_queries_per_minute": 60, "max_concurrent_queries": 5, "price_monthly": 29.0, "price_yearly": 290.0},
    {"name": "pro", "display_name": "Professional", "max_users": 50, "max_datasets": 100, "max_storage_mb": 10000, "max_ai_requests": 1000, "max_ai_tokens": 500000, "max_workflows": 50, "max_reports": 100, "max_dashboards": 50, "max_rag_documents": 500, "max_rag_storage_mb": 2000, "max_predictions": 200, "max_api_keys": 20, "max_queries_per_minute": 120, "max_concurrent_queries": 10, "price_monthly": 99.0, "price_yearly": 990.0},
    {"name": "enterprise", "display_name": "Enterprise", "max_users": 999999, "max_datasets": 999999, "max_storage_mb": 999999, "max_ai_requests": 999999, "max_ai_tokens": 999999, "max_workflows": 999999, "max_reports": 999999, "max_dashboards": 999999, "max_rag_documents": 999999, "max_rag_storage_mb": 999999, "max_predictions": 999999, "max_api_keys": 999999, "max_queries_per_minute": 999999, "max_concurrent_queries": 999999, "price_monthly": 499.0, "price_yearly": 4990.0},
]


class PlanService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def seed_plans(self) -> None:
        for plan_data in DEFAULT_PLANS:
            existing = self.db.query(Plan).filter(Plan.name == plan_data["name"]).first()
            if not existing:
                plan = Plan(id=str(uuid.uuid4()), **plan_data)
                self.db.add(plan)
        self.db.commit()

    def get_plan(self, name: str) -> Plan | None:
        return self.db.query(Plan).filter(Plan.name == name).first()

    def get_plan_by_id(self, plan_id: str) -> Plan | None:
        return self.db.query(Plan).filter(Plan.id == plan_id).first()

    def list_plans(self) -> list[dict[str, Any]]:
        plans = self.db.query(Plan).filter(Plan.is_active == True).order_by(Plan.price_monthly).all()
        return [self._to_dict(p) for p in plans]

    def create_plan(self, data: dict[str, Any]) -> dict[str, Any]:
        plan = Plan(id=str(uuid.uuid4()), **data)
        self.db.add(plan)
        self.db.commit()
        return self._to_dict(plan)

    def update_plan(self, plan_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        plan = self.get_plan_by_id(plan_id)
        if not plan:
            return None
        for k, v in data.items():
            if hasattr(plan, k):
                setattr(plan, k, v)
        plan.updated_at = datetime.utcnow()
        self.db.commit()
        return self._to_dict(plan)

    def _to_dict(self, plan: Plan) -> dict[str, Any]:
        return {c.name: getattr(plan, c.name) for c in plan.__table__.columns}
