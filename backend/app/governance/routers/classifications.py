"""Data classification API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization
from app.exceptions.handlers import NotFoundError

governance_classifications_router = APIRouter(
    prefix="/governance/classifications", tags=["Data Classification"]
)


@governance_classifications_router.get("")
async def list_classifications(
    resource_type: str | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.classification_service import ClassificationService

    service = ClassificationService(db)
    classifications = service.list_classifications(organization_id, resource_type=resource_type)
    return {
        "data": [
            {
                "id": c.id,
                "resource_type": c.resource_type,
                "resource_id": c.resource_id,
                "classification": c.classification,
                "sensitivity_tags": c.sensitivity_tags,
                "classified_by": c.classified_by,
                "classified_at": str(c.classified_at),
                "notes": c.notes,
            }
            for c in classifications
        ],
        "total": len(classifications),
    }


@governance_classifications_router.get("/{resource_type}/{resource_id}")
async def get_classification(
    resource_type: str,
    resource_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.classification_service import ClassificationService

    service = ClassificationService(db)
    cls = service.get_classification(resource_type, resource_id, organization_id)
    if not cls:
        raise NotFoundError("Classification not found")
    return {
        "id": cls.id,
        "classification": cls.classification,
        "sensitivity_tags": cls.sensitivity_tags,
    }


@governance_classifications_router.post("", status_code=201)
async def create_classification(
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.governance.services.classification_service import ClassificationService

    service = ClassificationService(db)
    cls = service.classify_resource(request, organization_id, user.get("sub", ""))
    return {"id": cls.id, "classification": cls.classification}
