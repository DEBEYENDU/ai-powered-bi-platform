"""MLOps Model Registry API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization
from app.exceptions.handlers import AppError, NotFoundError

mlops_models_router = APIRouter(prefix="/mlops/models", tags=["MLOps Models"])


# -- Global aggregate endpoints (MLOps overview page needs these) --


@mlops_models_router.get("/overview")
async def models_overview(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.model_registry import ModelRegistryService

    service = ModelRegistryService(db)
    models = service.list_models(organization_id)
    status_dist: dict[str, int] = {}
    total_versions = 0
    for m in models:
        status_dist[m.status] = status_dist.get(m.status, 0) + 1
        versions = service.list_versions(m.id, organization_id)
        total_versions += len(versions)
    return {
        "total_models": len(models),
        "total_versions": total_versions,
        "total_deployments": 0,
        "status_distribution": status_dist,
    }


@mlops_models_router.get("/monitoring/summary")
async def monitoring_summary(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    return {
        "total_predictions": 0,
        "avg_latency_ms": 0.0,
        "error_rate": 0.0,
        "drift_score": 0.0,
    }


@mlops_models_router.get("/drift/summary")
async def drift_summary(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    return {
        "total_checks": 0,
        "normal": 0,
        "warning": 0,
        "critical": 0,
    }


@mlops_models_router.get("")
async def list_models(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.model_registry import ModelRegistryService

    service = ModelRegistryService(db)
    models = service.list_models(organization_id, status=status)
    return {
        "data": [
            {
                "id": m.id,
                "name": m.name,
                "model_type": m.model_type,
                "task_type": m.task_type,
                "framework": m.framework,
                "status": m.status,
                "owner_id": m.owner_id,
                "created_at": str(m.created_at),
                "updated_at": str(m.updated_at),
            }
            for m in models
        ],
        "total": len(models),
    }


@mlops_models_router.get("/{model_id}")
async def get_model(
    model_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.model_registry import ModelRegistryService

    service = ModelRegistryService(db)
    model = service.get_model(model_id, organization_id)
    if not model:
        raise NotFoundError("Model not found")
    return {
        "id": model.id,
        "name": model.name,
        "description": model.description,
        "model_type": model.model_type,
        "task_type": model.task_type,
        "framework": model.framework,
        "status": model.status,
        "owner_id": model.owner_id,
        "tags": model.tags,
        "created_at": str(model.created_at),
        "updated_at": str(model.updated_at),
    }


@mlops_models_router.post("", status_code=201)
async def create_model(
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.model_registry import ModelRegistryService

    service = ModelRegistryService(db)
    model = service.create_model(request, organization_id, user.get("sub", ""))
    return {"id": model.id, "name": model.name, "status": model.status}


@mlops_models_router.put("/{model_id}")
async def update_model(
    model_id: str,
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.model_registry import ModelRegistryService

    service = ModelRegistryService(db)
    model = service.update_model(model_id, organization_id, request)
    if not model:
        raise NotFoundError("Model not found")
    return {"id": model.id, "name": model.name, "status": model.status}


@mlops_models_router.delete("/{model_id}")
async def delete_model(
    model_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.model_registry import ModelRegistryService

    service = ModelRegistryService(db)
    success = service.delete_model(model_id, organization_id)
    if not success:
        raise NotFoundError("Model not found")
    return {"success": True}


@mlops_models_router.get("/{model_id}/versions")
async def list_versions(
    model_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.model_registry import ModelRegistryService

    service = ModelRegistryService(db)
    versions = service.list_versions(model_id, organization_id)
    return {
        "data": [
            {
                "id": v.id,
                "version": v.version,
                "status": v.status,
                "metrics": v.metrics,
                "framework": v.framework,
                "is_active": v.is_active,
                "created_at": str(v.created_at),
            }
            for v in versions
        ],
        "total": len(versions),
    }


@mlops_models_router.post("/{model_id}/versions", status_code=201)
async def create_version(
    model_id: str,
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.model_registry import ModelRegistryService

    service = ModelRegistryService(db)
    version = service.create_version(model_id, organization_id, request, user.get("sub", ""))
    return {"id": version.id, "version": version.version, "status": version.status}


@mlops_models_router.get("/{model_id}/versions/{version}")
async def get_version(
    model_id: str,
    version: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.model_registry import ModelRegistryService

    service = ModelRegistryService(db)
    v = service.get_version_by_model_and_version(model_id, version, organization_id)
    if not v:
        raise NotFoundError("Version not found")
    return {
        "id": v.id,
        "version": v.version,
        "status": v.status,
        "metrics": v.metrics,
        "hyperparameters": v.hyperparameters,
        "framework": v.framework,
        "training_dataset_id": v.training_dataset_id,
        "is_active": v.is_active,
        "created_at": str(v.created_at),
    }


@mlops_models_router.post("/{model_id}/versions/{version_id}/promote")
async def promote_version(
    model_id: str,
    version_id: str,
    request: dict = Body({"target_environment": "production"}),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.model_registry import ModelRegistryService

    service = ModelRegistryService(db)
    try:
        v = service.promote_version(
            version_id, organization_id, request.get("target_environment", "production")
        )
    except Exception as exc:
        raise AppError(str(exc)) from None
    return {"success": True, "version": v.version, "status": v.status}


@mlops_models_router.post("/{model_id}/versions/{version_id}/archive")
async def archive_version(
    model_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.model_registry import ModelRegistryService

    service = ModelRegistryService(db)
    try:
        v = service.archive_version(version_id, organization_id)
    except Exception as exc:
        raise AppError(str(exc)) from None
    return {"success": True, "version": v.version, "status": v.status}


@mlops_models_router.post("/compare")
async def compare_versions(
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.model_registry import ModelRegistryService

    service = ModelRegistryService(db)
    results = service.compare_versions(request.get("version_ids", []), organization_id)
    return {"versions": results, "total": len(results)}


@mlops_models_router.get("/{model_id}/health")
async def model_health(
    model_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.deployment_service import DeploymentService

    service = DeploymentService(db)
    return service.get_health(model_id, organization_id)


@mlops_models_router.post("/{model_id}/predict")
async def predict(
    model_id: str,
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.serving_service import ServingService

    service = ServingService(db)
    try:
        result = service.predict(
            model_id, organization_id, request.get("input_data", {}), request.get("version")
        )
    except Exception as exc:
        raise AppError(str(exc)) from None
    return result


@mlops_models_router.get("/{model_id}/lifecycle")
async def model_lifecycle(
    model_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.lifecycle_service import LifecycleService

    service = LifecycleService(db)
    try:
        result = service.get_model_lifecycle(model_id, organization_id)
    except Exception as exc:
        raise AppError(str(exc)) from None
    return result


# -- Model-scoped aggregate endpoints (frontend needs these) --


@mlops_models_router.get("/{model_id}/training")
async def model_training_runs(
    model_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.training_service import TrainingService

    service = TrainingService(db)
    runs = service.list_runs(model_id=model_id, organization_id=organization_id)
    return {
        "data": [
            {
                "id": r.id,
                "experiment_id": r.experiment_id,
                "model_id": r.model_id,
                "status": r.status,
                "duration_seconds": r.duration_seconds,
                "metrics": r.metrics or {},
                "created_at": str(r.created_at),
            }
            for r in runs
        ],
        "total": len(runs),
    }


@mlops_models_router.get("/{model_id}/evaluations")
async def model_evaluations(
    model_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.model_registry import ModelRegistryService

    service = ModelRegistryService(db)
    versions = service.list_versions(model_id, organization_id)
    evaluations = []
    for v in versions:
        if v.metrics:
            for name, value in v.metrics.items():
                if isinstance(value, (int, float)):
                    evaluations.append(
                        {
                            "id": f"{v.id}_{name}",
                            "version_id": v.id,
                            "metric_name": name,
                            "metric_value": value,
                            "dataset": "validation",
                            "created_at": str(v.created_at),
                        }
                    )
    return {"data": evaluations, "total": len(evaluations)}


@mlops_models_router.get("/{model_id}/deployments")
async def model_deployments(
    model_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.deployment_service import DeploymentService

    service = DeploymentService(db)
    deployments = service.list_deployments(model_id=model_id, organization_id=organization_id)
    return {
        "data": [
            {
                "id": d.id,
                "model_version_id": d.model_version_id,
                "environment": d.environment,
                "status": d.status,
                "health": d.health,
                "deployed_at": str(d.deployed_at) if d.deployed_at else None,
            }
            for d in deployments
        ],
        "total": len(deployments),
    }


@mlops_models_router.get("/{model_id}/monitoring")
async def model_monitoring(
    model_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.monitoring_service import MonitoringService

    service = MonitoringService(db)
    metrics = service.get_metrics(model_id, organization_id)
    return {
        "data": [
            {
                "id": m.id,
                "timestamp": str(m.recorded_at),
                "predictions_count": m.metric_value if m.metric_name == "prediction_count" else 0,
                "avg_latency_ms": m.metric_value if m.metric_name == "latency_ms" else 0,
                "error_rate": m.metric_value if m.metric_name == "error_rate" else 0,
                "drift_score": m.metric_value if m.metric_name == "drift_score" else 0,
            }
            for m in metrics
        ],
        "total": len(metrics),
    }
