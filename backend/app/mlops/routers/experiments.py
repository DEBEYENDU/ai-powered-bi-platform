"""MLOps Experiments API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization
from app.exceptions.handlers import NotFoundError

mlops_experiments_router = APIRouter(prefix="/mlops/experiments", tags=["MLOps Experiments"])


@mlops_experiments_router.get("")
async def list_experiments(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.experiment_service import ExperimentService

    service = ExperimentService(db)
    experiments = service.list_experiments(organization_id)
    return {
        "data": [
            {
                "id": e.id,
                "name": e.name,
                "description": e.description,
                "objective": e.objective,
                "dataset_id": e.dataset_id,
                "status": e.status,
                "created_by": e.created_by,
                "created_at": str(e.created_at),
            }
            for e in experiments
        ],
        "total": len(experiments),
    }


@mlops_experiments_router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.experiment_service import ExperimentService

    service = ExperimentService(db)
    exp = service.get_experiment(experiment_id, organization_id)
    if not exp:
        raise NotFoundError("Experiment not found")
    return {
        "id": exp.id,
        "name": exp.name,
        "description": exp.description,
        "objective": exp.objective,
        "dataset_id": exp.dataset_id,
        "status": exp.status,
        "created_by": exp.created_by,
        "created_at": str(exp.created_at),
    }


@mlops_experiments_router.post("", status_code=201)
async def create_experiment(
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.experiment_service import ExperimentService

    service = ExperimentService(db)
    exp = service.create_experiment(request, organization_id, user.get("sub", ""))
    return {"id": exp.id, "name": exp.name, "status": exp.status}


@mlops_experiments_router.put("/{experiment_id}")
async def update_experiment(
    experiment_id: str,
    request: dict = Body(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.experiment_service import ExperimentService

    service = ExperimentService(db)
    exp = service.update_experiment(experiment_id, organization_id, request)
    if not exp:
        raise NotFoundError("Experiment not found")
    return {"id": exp.id, "name": exp.name, "status": exp.status}


@mlops_experiments_router.get("/{experiment_id}/runs")
async def list_runs(
    experiment_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.experiment_service import ExperimentService

    service = ExperimentService(db)
    runs = service.list_runs(experiment_id, organization_id)
    return {
        "data": [
            {
                "id": r.id,
                "status": r.status,
                "metrics": r.metrics,
                "parameters": r.parameters,
                "duration_ms": r.duration_ms,
                "created_at": str(r.created_at),
            }
            for r in runs
        ],
        "total": len(runs),
    }


@mlops_experiments_router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    from app.mlops.services.experiment_service import ExperimentService

    service = ExperimentService(db)
    run = service.get_run(run_id, organization_id)
    if not run:
        raise NotFoundError("Run not found")
    return {
        "id": run.id,
        "experiment_id": run.experiment_id,
        "status": run.status,
        "metrics": run.metrics,
        "parameters": run.parameters,
        "logs": run.logs,
        "error_message": run.error_message,
        "started_at": str(run.started_at) if run.started_at else None,
        "completed_at": str(run.completed_at) if run.completed_at else None,
        "duration_ms": run.duration_ms,
        "created_at": str(run.created_at),
    }
