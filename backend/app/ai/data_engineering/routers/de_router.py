"""AI Data Engineering router — all API endpoints for the data preparation platform."""

from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.ai.data_engineering.schemas import (
    CleanDatasetRequest,
    DatasetChatRequest,
    ExportDatasetRequest,
    ProfileDatasetRequest,
    TransformRequest,
    ValidateDatasetRequest,
)
from app.ai.data_engineering.services import data_loader, orchestrator
from app.ai.data_engineering.transformations.engine import get_available_transforms

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
) -> dict[str, Any]:
    """Upload a dataset (CSV, Excel, JSON, Parquet)."""
    content = await file.read()
    result = await orchestrator.upload_dataset(
        file_content=content,
        filename=file.filename or "upload.csv",
        name=name or file.filename or "Untitled",
        description=description,
        source_type=source_type,
    )
    return result.model_dump()


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@de_router.post("/profile")
async def profile_dataset(request: ProfileDatasetRequest) -> dict[str, Any]:
    """Profile a dataset — compute statistics, types, quality score."""
    result = await orchestrator.profile_single_dataset(request)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


@de_router.post("/validate")
async def validate_dataset(request: ValidateDatasetRequest) -> dict[str, Any]:
    """Validate dataset quality — detect issues and compute scores."""
    result = await orchestrator.validate_single_dataset(request)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------


@de_router.post("/clean")
async def clean_dataset(request: CleanDatasetRequest) -> dict[str, Any]:
    """Get cleaning suggestions and optionally auto-apply them."""
    result = await orchestrator.clean_single_dataset(request)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------


@de_router.post("/transform")
async def transform_dataset(request: TransformRequest) -> dict[str, Any]:
    """Apply transformations to a dataset."""
    result = await orchestrator.apply_dataset_transforms(request)
    return result.model_dump()


@de_router.get("/transforms")
async def list_transforms() -> list[dict[str, Any]]:
    """List all available transform types."""
    return get_available_transforms()


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


@de_router.post("/chat")
async def dataset_chat(request: DatasetChatRequest) -> dict[str, Any]:
    """Ask AI a question about a specific dataset."""
    result = await orchestrator.dataset_chat(request)
    return result


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@de_router.post("/export")
async def export_dataset(request: ExportDatasetRequest) -> dict[str, Any]:
    """Export a dataset in CSV, Excel, Parquet, JSON, or SQL format."""
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
async def export_dataset_download(request: ExportDatasetRequest) -> Response:
    """Export and return the file directly."""
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
async def list_datasets() -> dict[str, Any]:
    """List all stored datasets."""
    root = data_loader._storage_root()
    datasets: list[dict[str, Any]] = []
    for f in root.glob("*.parquet"):
        parts = f.stem.rsplit("_", 1)
        did = parts[0] if parts else f.stem
        try:
            df = pd.read_parquet(f)
            datasets.append(
                {
                    "dataset_id": did,
                    "name": f.name,
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "file_size": f.stat().st_size,
                }
            )
        except Exception:
            pass

    return {"datasets": datasets, "count": len(datasets)}


# ---------------------------------------------------------------------------
# Pipeline management
# ---------------------------------------------------------------------------


@de_router.get("/pipelines")
async def list_pipelines() -> dict[str, Any]:
    """List saved pipelines (placeholder — wired to DB in production)."""
    return {"pipelines": [], "count": 0}


# ---------------------------------------------------------------------------
# Schema inference
# ---------------------------------------------------------------------------


@de_router.get("/schema/{dataset_id}")
async def get_schema(dataset_id: str) -> dict[str, Any]:
    """Get inferred schema for a dataset."""
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
async def discover_relationships(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Discover relationships across multiple datasets."""
    # For now, return single-table relationships
    return {
        "relationships": [],
        "schema_type": "single_table",
        "message": "Upload multiple datasets to discover cross-table relationships",
    }
