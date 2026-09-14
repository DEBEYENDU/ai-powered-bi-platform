"""Governance policies API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization
from app.exceptions.handlers import NotFoundError

governance_policies_router = APIRouter(prefix="/governance/policies", tags=["Governance Policies"])


@governance_policies_router.get("")
async def list_policies(
    resource: str | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.policy_service import PolicyService

    service = PolicyService(db)
    policies = service.list_policies(organization_id, resource=resource)
    return {
        "data": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "resource": p.resource,
                "action": p.action,
                "effect": p.effect,
                "subject_type": p.subject_type,
                "subject_id": p.subject_id,
                "enabled": p.enabled,
                "priority": p.priority,
                "created_by": p.created_by,
                "created_at": str(p.created_at),
                "updated_at": str(p.updated_at),
            }
            for p in policies
        ],
        "total": len(policies),
    }


@governance_policies_router.get("/{policy_id}")
async def get_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.policy_service import PolicyService

    service = PolicyService(db)
    policy = service.get_policy(policy_id, organization_id)
    if not policy:
        raise NotFoundError("Policy not found")
    return {
        "id": policy.id,
        "name": policy.name,
        "resource": policy.resource,
        "action": policy.action,
        "effect": policy.effect,
        "conditions": policy.conditions,
        "enabled": policy.enabled,
    }


@governance_policies_router.post("", status_code=201)
async def create_policy(
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.policy_service import PolicyService

    service = PolicyService(db)
    policy = service.create_policy(request, organization_id, user.get("sub", ""))
    return {"id": policy.id, "name": policy.name, "effect": policy.effect}


@governance_policies_router.put("/{policy_id}")
async def update_policy(
    policy_id: str,
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.policy_service import PolicyService

    service = PolicyService(db)
    policy = service.update_policy(policy_id, organization_id, request)
    if not policy:
        raise NotFoundError("Policy not found")
    return {"id": policy.id, "name": policy.name, "effect": policy.effect}


@governance_policies_router.delete("/{policy_id}")
async def delete_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.policy_service import PolicyService

    service = PolicyService(db)
    success = service.delete_policy(policy_id, organization_id)
    if not success:
        raise NotFoundError("Policy not found")
    return {"success": True}


@governance_policies_router.post("/{policy_id}/toggle")
async def toggle_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.policy_service import PolicyService

    service = PolicyService(db)
    policy = service.toggle_policy(policy_id, organization_id)
    if not policy:
        raise NotFoundError("Policy not found")
    return {"id": policy.id, "enabled": policy.enabled}
