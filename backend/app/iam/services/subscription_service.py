"""Subscription management — plan assignment, lifecycle, provider abstraction."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.iam.models.tenant import Plan, Subscription
from app.iam.models.user import Organization

log = get_logger(__name__)


class BillingProvider:
    def create_customer(self, org: Organization) -> str | None:
        return None
    def create_subscription(self, customer_id: str, plan_name: str) -> str | None:
        return None
    def cancel_subscription(self, external_id: str) -> bool:
        return True
    def change_plan(self, external_id: str, new_plan_name: str) -> bool:
        return True
    def get_subscription(self, external_id: str) -> dict | None:
        return None
    def handle_webhook(self, payload: dict) -> dict | None:
        return None


class LocalBillingProvider(BillingProvider):
    pass


class SubscriptionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.billing: BillingProvider = LocalBillingProvider()

    def get_active_subscription(self, organization_id: str) -> Subscription | None:
        return (
            self.db.query(Subscription)
            .filter(
                Subscription.organization_id == organization_id,
                Subscription.status.in_(["trialing", "active"]),
            )
            .order_by(Subscription.created_at.desc())
            .first()
        )

    def get_plan_for_org(self, organization_id: str) -> Plan | None:
        sub = self.get_active_subscription(organization_id)
        if sub:
            return self.db.query(Plan).filter(Plan.id == sub.plan_id).first()
        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if org:
            return self.db.query(Plan).filter(Plan.name == org.plan).first()
        return self.db.query(Plan).filter(Plan.name == "free").first()

    def assign_plan(self, organization_id: str, plan_name: str, trial_days: int = 14) -> dict[str, Any]:
        plan = self.db.query(Plan).filter(Plan.name == plan_name).first()
        if not plan:
            raise ValueError(f"Plan '{plan_name}' not found")

        existing = self.get_active_subscription(organization_id)
        if existing:
            existing.status = "canceled"
            existing.canceled_at = datetime.utcnow()
            existing.updated_at = datetime.utcnow()

        now = datetime.utcnow()
        sub = Subscription(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            plan_id=plan.id,
            status="trialing" if trial_days > 0 else "active",
            starts_at=now,
            trial_ends_at=now + timedelta(days=trial_days) if trial_days > 0 else None,
        )
        self.db.add(sub)

        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if org:
            org.plan = plan_name
            org.updated_at = now

        self.db.commit()
        log.info("plan_assigned", org_id=organization_id, plan=plan_name)
        return {"subscription_id": sub.id, "plan": plan_name, "status": sub.status}

    def change_plan(self, organization_id: str, new_plan_name: str) -> dict[str, Any]:
        plan = self.db.query(Plan).filter(Plan.name == new_plan_name).first()
        if not plan:
            raise ValueError(f"Plan '{new_plan_name}' not found")

        sub = self.get_active_subscription(organization_id)
        if sub:
            sub.plan_id = plan.id
            sub.updated_at = datetime.utcnow()
        else:
            return self.assign_plan(organization_id, new_plan_name, trial_days=0)

        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if org:
            org.plan = new_plan_name
            org.updated_at = datetime.utcnow()

        self.db.commit()
        log.info("plan_changed", org_id=organization_id, new_plan=new_plan_name)
        return {"plan": new_plan_name, "status": sub.status if sub else "active"}

    def cancel(self, organization_id: str) -> dict[str, Any]:
        sub = self.get_active_subscription(organization_id)
        if sub:
            sub.status = "canceled"
            sub.canceled_at = datetime.utcnow()
            sub.updated_at = datetime.utcnow()
            self.db.commit()
        return {"canceled": True}
