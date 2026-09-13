"""Orchestrator — ties together profiling, validation, cleaning,
relationships, transformations, quality scoring, and AI services
into a single unified workflow."""

from __future__ import annotations

import time
from typing import Any

from app.ai.data_engineering.cleaning.cleaner import apply_cleaning, suggest_cleaning
from app.ai.data_engineering.profiling.profiler import profile_dataset
from app.ai.data_engineering.quality.scorer import compute_quality_score
from app.ai.data_engineering.schemas import (
    CleanDatasetRequest,
    CleanResponse,
    DatasetChatRequest,
    DatasetUploadResponse,
    ExportDatasetRequest,
    ProfileDatasetRequest,
    ProfileResponse,
    TransformRequest,
    TransformResponse,
    ValidateDatasetRequest,
    ValidationResponse,
)
from app.ai.data_engineering.services import ai_service, data_loader
from app.ai.data_engineering.transformations.engine import apply_transforms
from app.ai.data_engineering.validation.validator import validate_dataset

# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


async def upload_dataset(
    file_content: bytes,
    filename: str,
    name: str,
    description: str = "",
    source_type: str = "csv",
    organization_id: str = "",
) -> DatasetUploadResponse:
    """Upload and persist a dataset, returning metadata + preview."""
    try:
        df, dataset_id, file_size = data_loader.load_from_upload(
            file_content, filename, source_type
        )
        # Store as parquet for fast reload
        data_loader.save_dataframe(df, dataset_id, "v1")

        preview = df.head(5).to_dict(orient="records")

        return DatasetUploadResponse(
            success=True,
            dataset_id=dataset_id,
            name=name,
            row_count=len(df),
            column_count=len(df.columns),
            file_size=file_size,
            preview=preview,
        )
    except Exception as exc:
        return DatasetUploadResponse(
            success=False,
            name=name,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


async def profile_single_dataset(request: ProfileDatasetRequest) -> ProfileResponse:
    """Profile a single dataset."""
    try:
        df = data_loader.load_stored_dataset(request.dataset_id, "v1")
        result = profile_dataset(df)
        result["dataset_id"] = request.dataset_id

        # Get AI insights
        col_summary = "\n".join(
            f"- {c['name']}: {c['inferred_type']} (nulls={c['null_pct']}%)"
            for c in result["columns"]
        )
        insights = await ai_service.get_dataset_insights(
            name=request.dataset_id,
            row_count=result["row_count"],
            column_count=result["column_count"],
            column_profiles=col_summary,
        )
        result["ai_insights"] = insights

        return ProfileResponse(**result)
    except FileNotFoundError:
        return ProfileResponse(
            success=False,
            dataset_id=request.dataset_id,
            error="Dataset not found — upload it first",
        )
    except Exception as exc:
        return ProfileResponse(
            success=False,
            dataset_id=request.dataset_id,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


async def validate_single_dataset(request: ValidateDatasetRequest) -> ValidationResponse:
    """Validate a dataset against built-in checks + user rules."""
    t0 = time.perf_counter()
    try:
        df = data_loader.load_stored_dataset(request.dataset_id, "v1")
        issues, score = validate_dataset(df, rules=request.rules)

        [i.model_dump() for i in issues]

        return ValidationResponse(
            success=True,
            dataset_id=request.dataset_id,
            issues=issues,
            quality_score=score,
            total_checks=len(issues) + 5,
            passed_checks=5,
            failed_checks=len(issues),
            validation_time_ms=round((time.perf_counter() - t0) * 1000, 1),
        )
    except FileNotFoundError:
        return ValidationResponse(
            success=False,
            dataset_id=request.dataset_id,
            error="Dataset not found",
        )
    except Exception as exc:
        return ValidationResponse(
            success=False,
            dataset_id=request.dataset_id,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------


async def clean_single_dataset(request: CleanDatasetRequest) -> CleanResponse:
    """Generate cleaning suggestions and optionally apply them."""
    try:
        df = data_loader.load_stored_dataset(request.dataset_id, "v1")

        # Quality before
        score_before = compute_quality_score(df)

        # Get suggestions
        suggestions = suggest_cleaning(df)

        if request.auto_clean:
            applied_suggestions = [s for s in suggestions if s.auto_applicable]
        else:
            applied_suggestions = (
                suggestions
                if request.rules is None
                else [
                    s
                    for s in suggestions
                    if s.transform_type in [r.get("type", "") for r in request.rules]
                ]
            )

        rows_before = len(df)
        if applied_suggestions:
            cleaned, cells_modified = apply_cleaning(df, applied_suggestions)
            rows_after = len(cleaned)

            # Store cleaned version
            new_id = f"{request.dataset_id}_clean"
            data_loader.save_dataframe(cleaned, new_id, "v1")
            score_after = compute_quality_score(cleaned)
        else:
            cleaned = df
            rows_after = rows_before
            new_id = request.dataset_id
            cells_modified = 0
            score_after = score_before

        return CleanResponse(
            success=True,
            dataset_id=request.dataset_id,
            new_dataset_id=new_id,
            suggestions=suggestions,
            applied=[s.description for s in applied_suggestions],
            rows_before=rows_before,
            rows_after=rows_after,
            cells_modified=cells_modified,
            quality_before=score_before,
            quality_after=score_after,
        )
    except FileNotFoundError:
        return CleanResponse(
            success=False,
            dataset_id=request.dataset_id,
            error="Dataset not found",
        )
    except Exception as exc:
        return CleanResponse(
            success=False,
            dataset_id=request.dataset_id,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------


async def apply_dataset_transforms(request: TransformRequest) -> TransformResponse:
    """Apply a list of transformations to a dataset."""
    try:
        df = data_loader.load_stored_dataset(request.dataset_id, "v1")
        rows_before = len(df)
        set(df.columns)

        result_df, added, removed = apply_transforms(df, request.transforms)
        rows_after = len(result_df)

        # Store new version
        new_id = f"{request.dataset_id}_t"
        data_loader.save_dataframe(result_df, new_id, "v1")

        return TransformResponse(
            success=True,
            dataset_id=request.dataset_id,
            new_dataset_id=new_id,
            transforms_applied=len(request.transforms),
            rows_before=rows_before,
            rows_after=rows_after,
            columns_added=added,
            columns_removed=removed,
            version=1,
        )
    except FileNotFoundError:
        return TransformResponse(
            success=False,
            dataset_id=request.dataset_id,
            error="Dataset not found",
        )
    except Exception as exc:
        return TransformResponse(
            success=False,
            dataset_id=request.dataset_id,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


async def dataset_chat(request: DatasetChatRequest) -> dict[str, Any]:
    """Chat with AI about a specific dataset."""
    try:
        df = data_loader.load_stored_dataset(request.dataset_id, "v1")
        profile = profile_dataset(df)

        # Build context
        schema_text = f"Table: {request.dataset_id}\n"
        for col in profile["columns"]:
            schema_text += (
                f"  {col['name']}: {col['inferred_type']} "
                f"(nulls={col['null_pct']}%, unique={col['unique_pct']}%)\n"
            )

        profile_summary = (
            f"Rows: {profile['row_count']}, Columns: {profile['column_count']}\n"
            f"Quality Score: {profile['quality_score'].overall}/100\n"
            f"Missing cells: {profile['missing_cells']}\n"
            f"Duplicate rows: {profile['duplicates']}"
        )

        return await ai_service.chat(
            question=request.question,
            dataset_context=schema_text,
            profile_summary=profile_summary,
        )
    except FileNotFoundError:
        return {
            "answer": "Dataset not found. Please upload it first.",
            "confidence": "low",
            "evidence": [],
            "suggested_actions": [],
        }
    except Exception as exc:
        return {
            "answer": f"Error: {exc}",
            "confidence": "low",
            "evidence": [],
            "suggested_actions": [],
        }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


async def export_dataset(request: ExportDatasetRequest) -> dict[str, Any]:
    """Export a dataset in the requested format."""
    try:
        df = data_loader.load_stored_dataset(request.dataset_id, "v1")
        content, filename, mime = data_loader.export_dataframe(df, format=request.format)
        file_size = len(content)
        return {
            "success": True,
            "content": content,
            "filename": filename,
            "mime_type": mime,
            "file_size": file_size,
        }
    except FileNotFoundError:
        return {"success": False, "error": "Dataset not found"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
