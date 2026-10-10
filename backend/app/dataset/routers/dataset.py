"""Dataset endpoints (legacy ``/api/v1/datasets`` surface).

These share the storage layer and the ``de_datasets`` registry with
``/ai/de/*``: no endpoint here reports success unless real data was written,
and every read is scoped to the caller's organization.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.ai.data_engineering.models import DatasetRecord
from app.ai.data_engineering.services import data_loader, dataset_store
from app.dataset.schemas.dataset import DatasetCreate, DatasetOut
from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _out(record: DatasetRecord) -> dict:
    return DatasetOut(
        id=str(record.id),
        name=record.name,
        status=record.status,
        row_count=record.row_count,
        file_size=record.file_size,
    ).model_dump()


def _owned(db: Session, organization_id: str, dataset_id: str) -> DatasetRecord:
    record = dataset_store.resolve_record(db, organization_id, dataset_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return record


@router.post("/", response_model=DatasetOut)
async def create_dataset(
    data: DatasetCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Create an empty dataset record (a file is uploaded separately)."""
    try:
        record = dataset_store.register_dataset(
            db,
            dataset_id=str(uuid.uuid4()),
            organization_id=organization_id,
            owner_id=str(user.get("sub", "")),
            name=data.name,
            description=data.description or "",
            status="draft",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _out(record)


@router.post("/{dataset_id}/upload")
async def upload_file(
    dataset_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Attach a file to an existing dataset record."""
    record = _owned(db, organization_id, dataset_id)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    filename = file.filename or "upload.csv"
    suffix = Path(filename).suffix.lstrip(".").lower()
    source_type = "excel" if suffix in {"xls", "xlsx"} else (suffix or "csv")

    try:
        df, file_size = data_loader.store_upload(str(record.id), content, filename, source_type)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}") from exc

    record.storage_path = data_loader.save_dataframe(df, str(record.id), "v1")
    record.row_count = len(df)
    record.column_count = len(df.columns)
    record.file_size = file_size
    record.source_type = source_type
    record.status = "ready"
    db.commit()

    return {
        "dataset_id": str(record.id),
        "size": file_size,
        "row_count": record.row_count,
        "column_count": record.column_count,
        "status": record.status,
    }


@router.get("/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: str,
    rows: int = 10,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Return the first rows of a stored dataset."""
    record = _owned(db, organization_id, dataset_id)
    try:
        df = data_loader.load_stored_dataset(str(record.id), "v1")
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="No file has been uploaded for this dataset"
        ) from exc
    limit = max(1, min(rows, 200))
    return {
        "dataset_id": str(record.id),
        "rows": df.head(limit).to_dict(orient="records"),
        "row_count": len(df),
        "columns": list(df.columns),
    }


@router.get("/", response_model=list[DatasetOut])
async def list_datasets(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    return [_out(rec) for rec in dataset_store.list_datasets(db, organization_id)]
