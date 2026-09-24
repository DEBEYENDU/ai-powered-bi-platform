from fastapi import APIRouter, Depends

from app.dependencies.deps import get_current_user, require_organization

router = APIRouter(prefix="/etl", tags=["etl"])


@router.post("/jobs")
async def start_job(
    dataset_id: str,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    return {"job_id": "", "status": "pending"}


@router.get("/jobs/{job_id}")
async def job_status(
    job_id: str,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    return {"job_id": job_id, "status": "running"}
