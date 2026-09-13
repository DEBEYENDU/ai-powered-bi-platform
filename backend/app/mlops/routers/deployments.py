"""MLOps Deployments API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization
from app.exceptions.handlers import AppError, NotFoundError

mlops_deployments_router = APIRouter(prefix="/mlops/deployments", tags=["MLOps Deployments"])


@mlops_deployments_router.get("")
async def list_deployments(
    model_id: str | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.deployment_service import DeploymentService

    service = DeploymentService(db)
    deployments = service.list_deployments(organization_id, model_id=model_id)
    return {
        "data": [
            {
                "id": d.id,
                "model_id": d.model_id,
                "model_version_id": d.model_version_id,
                "environment": d.environment,
                "status": d.status,
                "health_status": d.health_status,
                "deployed_by": d.deployed_by,
                "deployed_at": str(d.deployed_at),
                "traffic_percentage": d.traffic_percentage,
            }
            for d in deployments
        ],
        "total": len(deployments),
    }


@mlops_deployments_router.get("/{deployment_id}")
async def get_deployment(
    deployment_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.deployment_service import DeploymentService

    service = DeploymentService(db)
    dep = service.get_deployment(deployment_id, organization_id)
    if not dep:
        raise NotFoundError("Deployment not found")
    return {
        "id": dep.id,
        "model_id": dep.model_id,
        "model_version_id": dep.model_version_id,
        "environment": dep.environment,
        "status": dep.status,
        "endpoint": dep.endpoint,
        "health_status": dep.health_status,
        "config": dep.config,
        "traffic_percentage": dep.traffic_percentage,
        "deployed_at": str(dep.deployed_at),
    }


@mlops_deployments_router.post("", status_code=201)
async def create_deployment(
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.deployment_service import DeploymentService

    service = DeploymentService(db)
    dep = service.create_deployment(request, organization_id, user.get("sub", ""))
    return {"id": dep.id, "environment": dep.environment, "status": dep.status}


@mlops_deployments_router.post("/{deployment_id}/activate")
async def activate_deployment(
    deployment_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.deployment_service import DeploymentService

    service = DeploymentService(db)
    try:
        dep = service.activate_deployment(deployment_id, organization_id)
    except Exception as exc:
        raise AppError(str(exc)) from None
    if not dep:
        raise NotFoundError("Deployment not found")
    return {"success": True, "status": dep.status}


@mlops_deployments_router.post("/{deployment_id}/stop")
async def stop_deployment(
    deployment_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.deployment_service import DeploymentService

    service = DeploymentService(db)
    try:
        dep = service.stop_deployment(deployment_id, organization_id)
    except Exception as exc:
        raise AppError(str(exc)) from None
    if not dep:
        raise NotFoundError("Deployment not found")
    return {"success": True, "status": dep.status}


@mlops_deployments_router.post("/{deployment_id}/rollback")
async def rollback_deployment(
    deployment_id: str,
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.deployment_service import DeploymentService

    service = DeploymentService(db)
    try:
        new_dep = service.rollback_deployment(
            deployment_id, organization_id, request.get("target_version_id", "")
        )
    except Exception as exc:
        raise AppError(str(exc)) from None
    return {"success": True, "new_deployment_id": new_dep.id, "status": new_dep.status}
