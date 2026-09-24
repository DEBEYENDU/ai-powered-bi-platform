"""Quota enforcement — check tenant limits before resource operations."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.iam.services.plan_service import PlanService
from app.iam.services.subscription_service import SubscriptionService
from app.iam.services.usage_service import UsageService

log = get_logger(__name__)


class QuotaExceeded(Exception):
    def __init__(self, resource: str, limit: int, current: int):
        self.resource = resource
        self.limit = limit
        self.current = current
        super().__init__(f"Quota exceeded for {resource}: {current}/{limit}")


class QuotaService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.plan_service = PlanService(db)
        self.subscription_service = SubscriptionService(db)
        self.usage_service = UsageService(db)

    def _plan_for_org(self, organization_id: str):
        plan = self.subscription_service.get_plan_for_org(organization_id)
        if not plan:
            plan = self.plan_service.get_plan("free")
        return plan

    def check_quota(self, organization_id: str, resource_type: str, quantity: int = 1) -> dict[str, Any]:
        plan = self._plan_for_org(organization_id)

        limit_attr = f"max_{resource_type}"
        limit = getattr(plan, limit_attr, 0) if plan else 0
        current = self.usage_service.get_current_month_usage(organization_id, resource_type)

        return {
            "allowed": (current + quantity) <= limit,
            "resource": resource_type,
            "limit": limit,
            "current": current,
            "remaining": max(0, limit - current),
            "plan": plan.name if plan else "free",
        }

    def enforce_quota(self, organization_id: str, resource_type: str, quantity: int = 1) -> None:
        result = self.check_quota(organization_id, resource_type, quantity)
        if not result["allowed"]:
            log.warning("quota_exceeded", org_id=organization_id, resource=resource_type, current=result["current"], limit=result["limit"])
            raise QuotaExceeded(resource_type, result["limit"], result["current"])

    def record_and_check(self, organization_id: str, resource_type: str, quantity: int = 1, **kwargs: Any) -> dict[str, Any]:
        self.enforce_quota(organization_id, resource_type, quantity)
        self.usage_service.record(organization_id, resource_type, quantity, **kwargs)
        return self.check_quota(organization_id, resource_type)

    def get_org_quotas(self, organization_id: str) -> dict[str, Any]:
        plan = self._plan_for_org(organization_id)
        usage = self.usage_service.get_usage_summary(organization_id)

        quotas = {}
        for key in dir(plan):
            if key.startswith("max_"):
                resource = key[4:]
                limit = getattr(plan, key, 0)
                quotas[resource] = {
                    "limit": limit,
                    "current": usage.get(resource, 0),
                    "remaining": max(0, limit - usage.get(resource, 0)),
                    "percentage": round((usage.get(resource, 0) / limit * 100), 1) if limit > 0 else 0,
                }
        return {"plan": plan.name, "quotas": quotas}
