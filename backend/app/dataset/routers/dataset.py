from fastapi import APIRouter, Depends, File, UploadFile

from app.dataset.schemas.dataset import DatasetCreate, DatasetOut
from app.dependencies.deps import get_current_user, require_organization

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/", response_model=DatasetOut)
async def create_dataset(
    data: DatasetCreate,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    return {"id": "", "name": data.name, "status": "draft", "row_count": 0, "file_size": 0}


@router.post("/{dataset_id}/upload")
async def upload_file(
    dataset_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    content = await file.read()
    return {"dataset_id": dataset_id, "size": len(content)}


@router.get("/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: str,
    rows: int = 10,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    return {"rows": []}


@router.get("/", response_model=list[DatasetOut])
async def list_datasets(
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    return []
