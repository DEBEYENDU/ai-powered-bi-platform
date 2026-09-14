"""Data retention API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization

governance_retention_router = APIRouter(prefix="/governance/retention", tags=["Data Retention"])


@governance_retention_router.get("")
async def list_retention_policies(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.retention_service import RetentionService

    service = RetentionService(db)
    policies = service.list_policies(organization_id)
    return {
        "data": [
            {
                "id": p.id,
                "name": p.name,
                "resource_type": p.resource_type,
                "retention_days": p.retention_days,
                "auto_delete": p.auto_delete,
                "legal_hold": p.legal_hold,
                "enabled": p.enabled,
                "created_at": str(p.created_at),
            }
            for p in policies
        ],
        "total": len(policies),
    }


@governance_retention_router.post("", status_code=201)
async def create_retention_policy(
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.retention_service import RetentionService

    service = RetentionService(db)
    policy = service.create_policy(request, organization_id, user.get("sub", ""))
    return {"id": policy.id, "name": policy.name, "retention_days": policy.retention_days}


@governance_retention_router.get("/check")
async def check_retention(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.retention_service import RetentionService

    service = RetentionService(db)
    return service.check_retention(organization_id)
