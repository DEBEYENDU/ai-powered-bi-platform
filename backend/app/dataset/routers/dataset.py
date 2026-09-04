from fastapi import APIRouter, File, UploadFile

from app.dataset.schemas.dataset import DatasetCreate, DatasetOut

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/", response_model=DatasetOut)
async def create_dataset(data: DatasetCreate):
    return {"id": "", "name": data.name, "status": "draft", "row_count": 0, "file_size": 0}


@router.post("/{dataset_id}/upload")
async def upload_file(dataset_id: str, file: UploadFile = File(...)):
    content = await file.read()
    return {"dataset_id": dataset_id, "size": len(content)}


@router.get("/{dataset_id}/preview")
async def preview_dataset(dataset_id: str, rows: int = 10):
    return {"rows": []}


@router.get("/", response_model=list[DatasetOut])
async def list_datasets():
    return []
