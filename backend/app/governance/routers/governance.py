"""Governance overview API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization

governance_router = APIRouter(prefix="/governance", tags=["Enterprise Governance"])


@governance_router.get("/overview")
async def governance_overview(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.authorization_service import AuthorizationService
    from app.governance.services.classification_service import ClassificationService
    from app.governance.services.policy_service import PolicyService
    from app.governance.services.security_service import SecurityService

    auth_svc = AuthorizationService(db)
    policy_svc = PolicyService(db)
    security_svc = SecurityService(db)
    class_svc = ClassificationService(db)

    permissions = auth_svc.get_user_permissions(user.get("sub", ""))
    policies = policy_svc.list_policies(organization_id)
    security_summary = security_svc.get_summary(organization_id, hours=24)
    classifications = class_svc.list_classifications(organization_id)

    return {
        "user_permissions": sorted(permissions),
        "total_policies": len(policies),
        "enabled_policies": sum(1 for p in policies if p.enabled),
        "total_classifications": len(classifications),
        "security_events_24h": security_summary["total_events"],
        "security_by_severity": security_summary["by_severity"],
    }


@governance_router.post("/authorize")
async def check_authorization(
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.authorization_service import AuthorizationService

    service = AuthorizationService(db)
    allowed = service.can(
        user_id=request.get("user_id", user.get("sub", "")),
        organization_id=request.get("organization_id", organization_id),
        action=request.get("action", ""),
        resource_type=request.get("resource_type", ""),
        resource_id=request.get("resource_id"),
    )
    return {"allowed": allowed}


@governance_router.get("/audit")
async def governance_audit(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.admin.services.platform import PlatformAdmin

    platform = PlatformAdmin()
    entries = platform.audit.query(organization_id=organization_id, limit=limit)
    return {"data": entries, "total": len(entries)}
