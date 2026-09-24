"""Tenant administration API — organization management, plans, usage, API keys."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization
from app.iam.models.tenant import TenantConfiguration
from app.iam.models.user import Organization
from app.iam.services.api_key_service import ApiKeyService
from app.iam.services.plan_service import PlanService
from app.iam.services.quota_service import QuotaService
from app.iam.services.subscription_service import SubscriptionService
from app.iam.services.usage_service import UsageService

tenant_router = APIRouter(prefix="/tenant", tags=["Tenant Management"])


def _get_db():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@tenant_router.get("/plans")
def list_plans(db: Session = Depends(_get_db)) -> dict[str, Any]:
    return {"data": PlanService(db).list_plans()}


@tenant_router.get("/plans/{plan_name}")
def get_plan(plan_name: str, db: Session = Depends(_get_db)) -> dict[str, Any]:
    plan = PlanService(db).get_plan(plan_name)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return {c.name: getattr(plan, c.name) for c in plan.__table__.columns}


@tenant_router.get("/current")
def get_current_tenant(
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(404, "Organization not found")
    plan = SubscriptionService(db).get_plan_for_org(organization_id)
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "status": org.status,
        "plan": org.plan,
        "created_at": org.created_at.isoformat(),
        "updated_at": org.updated_at.isoformat() if org.updated_at else None,
        "suspended_at": org.suspended_at.isoformat() if org.suspended_at else None,
        "plan_details": {c.name: getattr(plan, c.name) for c in plan.__table__.columns} if plan else None,
    }


@tenant_router.patch("/current")
def update_current_tenant(
    body: dict[str, Any] = Body(...),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(404, "Organization not found")
    for key in ["name"]:
        if key in body:
            setattr(org, key, body[key])
    org.updated_at = datetime.utcnow()
    db.commit()
    return {"updated": True}


@tenant_router.get("/usage")
def get_usage(
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    return {"usage": UsageService(db).get_usage_summary(organization_id)}


@tenant_router.get("/quotas")
def get_quotas(
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    return QuotaService(db).get_org_quotas(organization_id)


@tenant_router.get("/quotas/check")
def check_quota(
    resource: str = Query(...),
    quantity: int = Query(1),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    return QuotaService(db).check_quota(organization_id, resource, quantity)


@tenant_router.get("/api-keys")
def list_api_keys(
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    return {"data": ApiKeyService(db).list_keys(organization_id)}


@tenant_router.post("/api-keys")
def create_api_key(
    body: dict[str, Any] = Body(...),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    return ApiKeyService(db).create_key(
        organization_id,
        name=body.get("name", "API Key"),
        scopes=body.get("scopes", "*"),
        expires_in_days=body.get("expires_in_days"),
        created_by=user.get("sub"),
    )


@tenant_router.delete("/api-keys/{key_id}")
def revoke_api_key(
    key_id: str,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    if not ApiKeyService(db).revoke_key(organization_id, key_id):
        raise HTTPException(404, "API key not found")
    return {"revoked": True}


@tenant_router.get("/config")
def get_tenant_config(
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    config = db.query(TenantConfiguration).filter(
        TenantConfiguration.organization_id == organization_id
    ).first()
    if not config:
        config = TenantConfiguration(id=uuid.uuid4().hex, organization_id=organization_id)
        db.add(config)
        db.commit()
    return {
        "timezone": config.timezone or "UTC",
        "locale": config.locale or "en",
        "branding": config.branding_json,
        "ai_preferences": config.ai_preferences_json,
        "retention_days": config.retention_days,
        "custom_settings": config.custom_settings_json,
    }


@tenant_router.patch("/config")
def update_tenant_config(
    body: dict[str, Any] = Body(...),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
    db: Session = Depends(_get_db),
) -> dict[str, Any]:
    config = db.query(TenantConfiguration).filter(
        TenantConfiguration.organization_id == organization_id
    ).first()
    if not config:
        config = TenantConfiguration(id=uuid.uuid4().hex, organization_id=organization_id)
        db.add(config)
    field_map = {
        "timezone": "timezone",
        "locale": "locale",
        "branding": "branding_json",
        "branding_json": "branding_json",
        "ai_preferences": "ai_preferences_json",
        "ai_preferences_json": "ai_preferences_json",
        "retention_days": "retention_days",
        "custom_settings": "custom_settings_json",
        "custom_settings_json": "custom_settings_json",
    }
    for key in field_map:
        if key in body:
            setattr(config, field_map[key], body[key])
    config.updated_at = datetime.utcnow()
    db.commit()
    return {"updated": True}
