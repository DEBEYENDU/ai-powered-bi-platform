"""MLOps Drift Detection API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization

mlops_drift_router = APIRouter(prefix="/mlops/drift", tags=["MLOps Drift Detection"])


@mlops_drift_router.post("/data")
async def check_data_drift(
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.drift_service import DriftService

    service = DriftService(db)
    result = service.check_data_drift(
        request.get("model_id", ""),
        organization_id,
        request.get("reference_stats", {}),
        request.get("current_stats", {}),
    )
    return result


@mlops_drift_router.post("/prediction")
async def check_prediction_drift(
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.drift_service import DriftService

    service = DriftService(db)
    result = service.check_prediction_drift(
        request.get("model_id", ""),
        organization_id,
        request.get("historical_predictions", []),
        request.get("recent_predictions", []),
    )
    return result


@mlops_drift_router.get("/{model_id}/history")
async def get_drift_history(
    model_id: str,
    days: int = 30,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.drift_service import DriftService

    service = DriftService(db)
    records = service.get_drift_history(model_id, organization_id, days=days)
    return {
        "data": [
            {
                "id": r.id,
                "metric_type": r.metric_type,
                "metric_name": r.metric_name,
                "metric_value": r.metric_value,
                "status": r.status,
                "message": r.message,
                "recorded_at": str(r.recorded_at),
            }
            for r in records
        ],
        "total": len(records),
    }
