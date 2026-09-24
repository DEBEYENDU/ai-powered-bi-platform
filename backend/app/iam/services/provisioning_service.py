"""Tenant provisioning — idempotent setup of new organizations."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.iam.models.tenant import TenantConfiguration
from app.iam.models.user import Organization
from app.iam.services.plan_service import PlanService
from app.iam.services.subscription_service import SubscriptionService

log = get_logger(__name__)


class ProvisioningService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.plan_service = PlanService(db)
        self.subscription_service = SubscriptionService(db)

    def provision_tenant(self, name: str, slug: str, owner_id: str | None = None, plan_name: str = "free", trial_days: int = 14) -> dict[str, Any]:
        self.plan_service.seed_plans()
        existing = self.db.query(Organization).filter(Organization.slug == slug).first()
        if existing:
            return {"organization_id": existing.id, "status": "already_exists"}

        org = Organization(
            id=str(uuid.uuid4()),
            name=name,
            slug=slug,
            owner_id=owner_id,
            status="active",
            plan=plan_name,
            created_at=datetime.utcnow(),
        )
        self.db.add(org)
        self.db.flush()

        config = TenantConfiguration(
            id=str(uuid.uuid4()),
            organization_id=org.id,
        )
        self.db.add(config)

        self.db.commit()
        self.subscription_service.assign_plan(org.id, plan_name, trial_days=trial_days)

        log.info("tenant_provisioned", org_id=org.id, name=name, plan=plan_name)
        return {"organization_id": org.id, "status": "provisioned", "plan": plan_name}

    def suspend_tenant(self, organization_id: str) -> dict[str, Any]:
        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise ValueError("Organization not found")
        org.status = "suspended"
        org.suspended = True
        org.suspended_at = datetime.utcnow()
        org.updated_at = datetime.utcnow()
        self.db.commit()
        log.info("tenant_suspended", org_id=organization_id)
        return {"status": "suspended"}

    def reactivate_tenant(self, organization_id: str) -> dict[str, Any]:
        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise ValueError("Organization not found")
        org.status = "active"
        org.suspended = False
        org.suspended_at = None
        org.updated_at = datetime.utcnow()
        self.db.commit()
        log.info("tenant_reactivated", org_id=organization_id)
        return {"status": "active"}

    def soft_delete_tenant(self, organization_id: str) -> dict[str, Any]:
        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise ValueError("Organization not found")
        org.status = "deleted"
        org.deleted_at = datetime.utcnow()
        org.updated_at = datetime.utcnow()
        self.db.commit()
        log.info("tenant_deleted", org_id=organization_id)
        return {"status": "deleted"}
