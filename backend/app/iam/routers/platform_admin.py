"""Platform administration — tenant management, lifecycle, billing."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.deps import get_current_user
from app.iam.models.user import Organization
from app.iam.services.provisioning_service import ProvisioningService
from app.iam.services.quota_service import QuotaService
from app.iam.services.subscription_service import SubscriptionService
from app.iam.services.usage_service import UsageService

platform_admin_router = APIRouter(prefix="/admin/tenants", tags=["Platform Admin - Tenants"])


def _get_db():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@platform_admin_router.get("")
def list_tenants(
    status: str | None = Query(None),
    plan: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    q = db.query(Organization).filter(Organization.deleted_at.is_(None))
    if status:
        q = q.filter(Organization.status == status)
    if plan:
        q = q.filter(Organization.plan == plan)
    total = q.count()
    orgs = q.order_by(Organization.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "data": [
            {
                "id": o.id, "name": o.name, "slug": o.slug, "status": o.status,
                "plan": o.plan, "created_at": o.created_at.isoformat(),
                "suspended_at": o.suspended_at.isoformat() if o.suspended_at else None,
            }
            for o in orgs
        ],
        "total": total,
    }


@platform_admin_router.post("")
def create_tenant(
    body: dict[str, Any] = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    return ProvisioningService(db).provision_tenant(
        name=body.get("name", "New Organization"),
        slug=body.get("slug", ""),
        plan_name=body.get("plan", "free"),
    )


@platform_admin_router.get("/{tenant_id}")
def get_tenant(
    tenant_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    org = db.query(Organization).filter(Organization.id == tenant_id).first()
    if not org:
        raise HTTPException(404, "Tenant not found")
    usage = UsageService(db).get_usage_summary(tenant_id)
    return {
        "id": org.id, "name": org.name, "slug": org.slug,
        "status": org.status, "plan": org.plan,
        "created_at": org.created_at.isoformat(),
        "updated_at": org.updated_at.isoformat() if org.updated_at else None,
        "suspended_at": org.suspended_at.isoformat() if org.suspended_at else None,
        "usage": usage,
    }


@platform_admin_router.post("/{tenant_id}/suspend")
def suspend_tenant(
    tenant_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    return ProvisioningService(db).suspend_tenant(tenant_id)


@platform_admin_router.post("/{tenant_id}/reactivate")
def reactivate_tenant(
    tenant_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    return ProvisioningService(db).reactivate_tenant(tenant_id)


@platform_admin_router.post("/{tenant_id}/plan")
def change_tenant_plan(
    tenant_id: str,
    body: dict[str, Any] = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    return SubscriptionService(db).change_plan(tenant_id, body.get("plan", "free"))


@platform_admin_router.get("/{tenant_id}/usage")
def get_tenant_usage(
    tenant_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    return {"usage": UsageService(db).get_usage_summary(tenant_id)}


@platform_admin_router.get("/{tenant_id}/quotas")
def get_tenant_quotas(
    tenant_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    return QuotaService(db).get_org_quotas(tenant_id)


@platform_admin_router.delete("/{tenant_id}")
def delete_tenant(
    tenant_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    return ProvisioningService(db).soft_delete_tenant(tenant_id)
