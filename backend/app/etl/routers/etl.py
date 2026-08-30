from fastapi import APIRouter
router = APIRouter(prefix="/etl", tags=["etl"])

@router.post("/jobs")
async def start_job(dataset_id: str):
    return {"job_id":"", "status":"pending"}

@router.get("/jobs/{job_id}")
async def job_status(job_id: str):
    return {"job_id": job_id, "status":"running"}
