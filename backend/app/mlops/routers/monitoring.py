"""MLOps Monitoring API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization

mlops_monitoring_router = APIRouter(prefix="/mlops/monitoring", tags=["MLOps Monitoring"])


@mlops_monitoring_router.get("/{model_id}/summary")
async def get_monitoring_summary(
    model_id: str,
    hours: int = 24,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.monitoring_service import MonitoringService

    service = MonitoringService(db)
    return service.get_summary(model_id, organization_id, hours=hours)


@mlops_monitoring_router.get("/{model_id}/metrics")
async def get_monitoring_metrics(
    model_id: str,
    metric_type: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.monitoring_service import MonitoringService

    service = MonitoringService(db)
    records = service.get_metrics(model_id, organization_id, metric_type=metric_type, limit=limit)
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


@mlops_monitoring_router.get("/{model_id}/alerts")
async def get_monitoring_alerts(
    model_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.monitoring_service import MonitoringService

    service = MonitoringService(db)
    alerts = service.check_alerts(model_id, organization_id)
    return {"alerts": alerts, "total": len(alerts)}


@mlops_monitoring_router.post("/{model_id}/record")
async def record_metric(
    model_id: str,
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.monitoring_service import MonitoringService

    service = MonitoringService(db)
    record = service.record_metric(
        model_id,
        organization_id,
        request.get("metric_type", ""),
        request.get("metric_name", ""),
        request.get("metric_value", 0.0),
        request.get("dimensions"),
        request.get("model_version_id"),
    )
    return {"id": record.id, "metric_name": record.metric_name, "metric_value": record.metric_value}
