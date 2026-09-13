"""MLOps Model Registry API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization
from app.exceptions.handlers import AppError, NotFoundError

mlops_models_router = APIRouter(prefix="/mlops/models", tags=["MLOps Models"])


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
