"""Governance security API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization

governance_security_router = APIRouter(prefix="/governance/security", tags=["Governance Security"])


@governance_security_router.get("/events")
async def list_events(
    event_type: str | None = None,
    severity: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.security_service import SecurityService

    service = SecurityService(db)
    events = service.get_events(
        organization_id, event_type=event_type, severity=severity, limit=limit
    )
    return {
        "data": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "severity": e.severity,
                "actor_id": e.actor_id,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "action": e.action,
                "outcome": e.outcome,
                "details": e.details,
                "source_ip": e.source_ip,
                "created_at": str(e.created_at),
            }
            for e in events
        ],
        "total": len(events),
    }


@governance_security_router.get("/summary")
async def security_summary(
    hours: int = 24,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.security_service import SecurityService

    service = SecurityService(db)
    return service.get_summary(organization_id, hours=hours)


@governance_security_router.post("/check")
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
    return {
        "allowed": allowed,
        "reason": "" if allowed else "Access denied by authorization policy",
    }
