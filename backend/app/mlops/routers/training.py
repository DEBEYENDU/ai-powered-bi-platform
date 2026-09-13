"""MLOps Training API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization
from app.exceptions.handlers import NotFoundError

mlops_training_router = APIRouter(prefix="/mlops/training", tags=["MLOps Training"])


@mlops_training_router.post("", status_code=201)
async def start_training(
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.training_service import TrainingService

    service = TrainingService(db)
    run = service.start_training(request, organization_id, user.get("sub", ""))
    return {"id": run.id, "status": run.status, "experiment_id": run.experiment_id}


@mlops_training_router.get("/{run_id}")
async def get_training_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.training_service import TrainingService

    service = TrainingService(db)
    run = service.get_run(run_id, organization_id)
    if not run:
        raise NotFoundError("Training run not found")
    return {
        "id": run.id,
        "experiment_id": run.experiment_id,
        "status": run.status,
        "metrics": run.metrics,
        "parameters": run.parameters,
        "logs": run.logs,
        "error_message": run.error_message,
        "duration_ms": run.duration_ms,
        "started_at": str(run.started_at) if run.started_at else None,
        "completed_at": str(run.completed_at) if run.completed_at else None,
        "created_at": str(run.created_at),
    }


@mlops_training_router.post("/{run_id}/cancel")
async def cancel_training(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.training_service import TrainingService

    service = TrainingService(db)
    run = service.cancel_training(run_id, organization_id)
    if not run:
        raise NotFoundError("Training run not found or cannot be cancelled")
    return {"success": True, "run_id": run_id, "status": "cancelled"}


@mlops_training_router.post("/{run_id}/complete")
async def complete_training(
    run_id: str,
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.training_service import TrainingService

    service = TrainingService(db)
    run = service.complete_training(
        run_id, organization_id, request.get("metrics", {}), request.get("artifact_path", "")
    )
    if not run:
        raise NotFoundError("Training run not found")
    return {"success": True, "run_id": run_id, "status": "completed", "metrics": run.metrics}


@mlops_training_router.get("")
async def list_training_runs(
    model_id: str | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.training_service import TrainingService

    service = TrainingService(db)
    runs = service.list_runs(organization_id, model_id=model_id)
    return {
        "data": [
            {
                "id": r.id,
                "experiment_id": r.experiment_id,
                "model_id": r.model_id,
                "status": r.status,
                "metrics": r.metrics,
                "duration_ms": r.duration_ms,
                "created_at": str(r.created_at),
            }
            for r in runs
        ],
        "total": len(runs),
    }
