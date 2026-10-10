"""AI Data Engineering router — all API endpoints for the data preparation platform."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.ai.data_engineering.schemas import (
    CleanDatasetRequest,
    DatasetChatRequest,
    ExportDatasetRequest,
    ProfileDatasetRequest,
    TransformRequest,
    ValidateDatasetRequest,
)
from app.ai.data_engineering.services import data_loader, dataset_store, orchestrator
from app.ai.data_engineering.transformations.engine import get_available_transforms
from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization

de_router = APIRouter(prefix="/ai/de", tags=["AI Data Engineering"])


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@de_router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(""),
    description: str = Form(""),
    source_type: str = Form("csv"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Upload a dataset (CSV, Excel, JSON, Parquet)."""
    content = await file.read()
    result = await orchestrator.upload_dataset(
        file_content=content,
        filename=file.filename or "upload.csv",
        name=name or file.filename or "Untitled",
        description=description,
        source_type=source_type,
        db=db,
        organization_id=organization_id,
        owner_id=str(user.get("sub", "")),
    )
    return result.model_dump()


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@de_router.post("/profile")
async def profile_dataset(
    request: ProfileDatasetRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Profile a dataset — compute statistics, types, quality score."""
    if not dataset_store.owns_dataset(db, organization_id, request.dataset_id):
        return {
            "success": False,
            "dataset_id": request.dataset_id,
            "error": "Dataset not found",
        }
    result = await orchestrator.profile_single_dataset(request)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


@de_router.post("/validate")
async def validate_dataset(
    request: ValidateDatasetRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Validate dataset quality — detect issues and compute scores."""
    if not dataset_store.owns_dataset(db, organization_id, request.dataset_id):
        return {
            "success": False,
            "dataset_id": request.dataset_id,
            "error": "Dataset not found",
        }
    result = await orchestrator.validate_single_dataset(request)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------


@de_router.post("/clean")
async def clean_dataset(
    request: CleanDatasetRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Get cleaning suggestions and optionally auto-apply them."""
    if not dataset_store.owns_dataset(db, organization_id, request.dataset_id):
        return {
            "success": False,
            "dataset_id": request.dataset_id,
            "error": "Dataset not found",
        }
    result = await orchestrator.clean_single_dataset(request)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------


@de_router.post("/transform")
async def transform_dataset(
    request: TransformRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Apply transformations to a dataset."""
    if not dataset_store.owns_dataset(db, organization_id, request.dataset_id):
        return {
            "success": False,
            "dataset_id": request.dataset_id,
            "error": "Dataset not found",
        }
    result = await orchestrator.apply_dataset_transforms(request)
    return result.model_dump()


@de_router.get("/transforms")
async def list_transforms(
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> list[dict[str, Any]]:
    """List all available transform types."""
    return get_available_transforms()


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


@de_router.post("/chat")
async def dataset_chat(
    request: DatasetChatRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Ask AI a question about a specific dataset."""
    record = dataset_store.resolve_record(db, organization_id, request.dataset_id)
    if record is None:
        return {
            "answer": "Dataset not found. Please upload it first.",
            "confidence": "low",
            "evidence": [],
            "suggested_actions": [],
        }
    result = await orchestrator.dataset_chat(request, dataset_name=record.name)
    return result


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@de_router.post("/export")
async def export_dataset(
    request: ExportDatasetRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Export a dataset in CSV, Excel, Parquet, JSON, or SQL format."""
    if not dataset_store.owns_dataset(db, organization_id, request.dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    result = await orchestrator.export_dataset(request)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Export failed"))
    return {
        "success": True,
        "filename": result["filename"],
        "file_size": result["file_size"],
        "format": request.format,
    }


@de_router.post("/export/download")
async def export_dataset_download(
    request: ExportDatasetRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> Response:
    """Export and return the file directly."""
    if not dataset_store.owns_dataset(db, organization_id, request.dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    result = await orchestrator.export_dataset(request)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Export failed"))
    return Response(
        content=result["content"],
        media_type=result["mime_type"],
        headers={"Content-Disposition": f"attachment; filename={result['filename']}"},
    )


# ---------------------------------------------------------------------------
# Datasets listing
# ---------------------------------------------------------------------------


@de_router.get("/datasets")
async def list_datasets(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """List the datasets uploaded by this organization."""
    datasets: list[dict[str, Any]] = []
    for rec in dataset_store.list_datasets(db, organization_id):
        datasets.append(
            {
                "dataset_id": str(rec.id),
                "name": rec.name,
                "description": rec.description,
                "source_type": rec.source_type,
                "status": rec.status,
                "row_count": rec.row_count,
                "column_count": rec.column_count,
                "file_size": rec.file_size,
                "created_at": rec.created_at.isoformat() if rec.created_at else None,
            }
        )

    return {"datasets": datasets, "count": len(datasets)}


# ---------------------------------------------------------------------------
# Pipeline management
# ---------------------------------------------------------------------------


@de_router.get("/pipelines")
async def list_pipelines(
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """List saved pipelines (placeholder — wired to DB in production)."""
    return {"pipelines": [], "count": 0}


@de_router.post("/pipelines")
async def create_pipeline(
    body: dict[str, Any] | None = None,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Create a pipeline definition (placeholder — wired to DB in production)."""
    import uuid

    pipeline_id = str(uuid.uuid4())[:8]
    return {
        "pipeline": {
            "id": pipeline_id,
            "name": (body or {}).get("name", "Untitled"),
            "dataset_id": (body or {}).get("dataset_id", ""),
            "steps": (body or {}).get("steps", []),
            "status": "draft",
            "run_count": 0,
            "created_at": __import__("datetime").datetime.utcnow().isoformat(),
        }
    }


@de_router.post("/pipelines/run")
async def run_pipeline(
    body: dict[str, Any] | None = None,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Run a pipeline (placeholder — wired to DB + Celery in production)."""
    return {
        "status": "started",
        "pipeline_id": (body or {}).get("pipeline_id", ""),
        "run_id": __import__("uuid").uuid4().hex[:8],
    }


@de_router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: str,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Delete a pipeline (placeholder — wired to DB in production)."""
    return {"deleted": True, "pipeline_id": pipeline_id}


# ---------------------------------------------------------------------------
# Schema inference
# ---------------------------------------------------------------------------


@de_router.get("/schema/{dataset_id}")
async def get_schema(
    dataset_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Get inferred schema for a dataset."""
    if not dataset_store.owns_dataset(db, organization_id, dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    try:
        df = data_loader.load_stored_dataset(dataset_id, "v1")
        from app.ai.data_engineering.schema.inferencer import infer_table_schema

        schema = infer_table_schema(df, dataset_id)
        return schema.model_dump()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset not found")


# ---------------------------------------------------------------------------
# Relationship discovery
# ---------------------------------------------------------------------------


@de_router.post("/relationships")
async def discover_relationships(
    body: dict[str, Any] | None = None,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Discover relationships across multiple datasets."""
    # For now, return single-table relationships
    return {
        "relationships": [],
        "schema_type": "single_table",
        "message": "Upload multiple datasets to discover cross-table relationships",
    }
