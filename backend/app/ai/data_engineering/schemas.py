"""Request / response schemas for the AI Data Engineering platform."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DataSourceType(str, Enum):
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    PARQUET = "parquet"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    API = "api"


class QualityDimension(str, Enum):
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    ACCURACY = "accuracy"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"
    TIMELINESS = "timeliness"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TransformType(str, Enum):
    FILL_MISSING = "fill_missing"
    REMOVE_DUPLICATES = "remove_duplicates"
    STANDARDIZE = "standardize"
    NORMALIZE_TEXT = "normalize_text"
    TRIM_SPACES = "trim_spaces"
    CONVERT_TYPE = "convert_type"
    SPLIT_COLUMN = "split_column"
    MERGE_COLUMNS = "merge_columns"
    PIVOT = "pivot"
    UNPIVOT = "unpivot"
    GROUP_AGGREGATE = "group_aggregate"
    CALCULATED_COLUMN = "calculated_column"
    RENAME = "rename"
    DROP = "drop"
    FILTER = "filter"


class PipelineStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"


# --- Request ---


class UploadDatasetRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    source_type: DataSourceType = DataSourceType.CSV
    organization_id: str | None = None


class ProfileDatasetRequest(BaseModel):
    dataset_id: str


class ValidateDatasetRequest(BaseModel):
    dataset_id: str
    rules: list[dict[str, Any]] | None = None


class CleanDatasetRequest(BaseModel):
    dataset_id: str
    auto_clean: bool = True
    rules: list[dict[str, Any]] | None = None


class TransformRequest(BaseModel):
    dataset_id: str
    transforms: list[dict[str, Any]]
    create_version: bool = True


class PipelineCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    dataset_id: str
    steps: list[dict[str, Any]] = Field(default_factory=list)
    schedule: str | None = None


class PipelineRunRequest(BaseModel):
    pipeline_id: str


class DatasetChatRequest(BaseModel):
    dataset_id: str
    question: str = Field(..., min_length=1)


class ExportDatasetRequest(BaseModel):
    dataset_id: str
    format: str = "csv"
    include_transforms: bool = True


# --- Nested data ---


class ColumnProfile(BaseModel):
    name: str
    dtype: str = ""
    non_null_count: int = 0
    null_count: int = 0
    null_pct: float = 0.0
    unique_count: int = 0
    unique_pct: float = 0.0
    duplicate_count: int = 0
    duplicate_pct: float = 0.0
    min_value: Any = None
    max_value: Any = None
    mean_value: float | None = None
    median_value: float | None = None
    std_value: float | None = None
    skewness: float | None = None
    kurtosis: float | None = None
    top_values: list[dict[str, Any]] = Field(default_factory=list)
    inferred_type: str = ""
    detected_format: str = ""


class QualityIssue(BaseModel):
    id: str = ""
    dimension: str
    severity: str
    column: str = ""
    issue_type: str
    description: str
    affected_rows: int = 0
    affected_pct: float = 0.0
    suggestion: str = ""


class QualityScore(BaseModel):
    overall: float = 0.0
    completeness: float = 0.0
    consistency: float = 0.0
    accuracy: float = 0.0
    uniqueness: float = 0.0
    validity: float = 0.0
    timeliness: float = 0.0


class CleaningSuggestion(BaseModel):
    id: str = ""
    column: str
    transform_type: str
    description: str
    current_state: str = ""
    proposed_state: str = ""
    affected_rows: int = 0
    confidence: float = 0.0
    auto_applicable: bool = False
    parameters: dict[str, Any] = Field(default_factory=dict)


class Relationship(BaseModel):
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    relationship_type: str = "many_to_one"
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)


class TransformStep(BaseModel):
    step_id: str = ""
    transform_type: str
    column: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    order: int = 0


class Pipeline(BaseModel):
    id: str = ""
    name: str
    description: str = ""
    dataset_id: str
    steps: list[TransformStep] = Field(default_factory=list)
    status: str = "draft"
    schedule: str | None = None
    last_run: str | None = None
    created_at: str = ""


class DatasetVersion(BaseModel):
    version: int
    created_at: str
    row_count: int = 0
    quality_score: float = 0.0
    change_summary: str = ""


class SchemaInfo(BaseModel):
    table_name: str
    columns: list[dict[str, Any]] = Field(default_factory=list)
    primary_keys: list[str] = Field(default_factory=list)
    foreign_keys: list[dict[str, str]] = Field(default_factory=list)
    row_count: int = 0
    inferred_purpose: str = ""


class RelationshipGraph(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    schema_type: str = ""


# --- Response ---


class DatasetUploadResponse(BaseModel):
    success: bool
    dataset_id: str = ""
    name: str = ""
    row_count: int = 0
    column_count: int = 0
    file_size: int = 0
    preview: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class ProfileResponse(BaseModel):
    success: bool
    dataset_id: str
    row_count: int = 0
    column_count: int = 0
    columns: list[ColumnProfile] = Field(default_factory=list)
    duplicates: int = 0
    missing_cells: int = 0
    quality_score: QualityScore = Field(default_factory=QualityScore)
    ai_insights: list[str] = Field(default_factory=list)
    profile_time_ms: float = 0.0
    error: str | None = None


class ValidationResponse(BaseModel):
    success: bool
    dataset_id: str
    issues: list[QualityIssue] = Field(default_factory=list)
    quality_score: QualityScore = Field(default_factory=QualityScore)
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    validation_time_ms: float = 0.0
    error: str | None = None


class CleanResponse(BaseModel):
    success: bool
    dataset_id: str
    new_dataset_id: str = ""
    suggestions: list[CleaningSuggestion] = Field(default_factory=list)
    applied: list[str] = Field(default_factory=list)
    rows_before: int = 0
    rows_after: int = 0
    cells_modified: int = 0
    quality_before: QualityScore = Field(default_factory=QualityScore)
    quality_after: QualityScore = Field(default_factory=QualityScore)
    error: str | None = None


class TransformResponse(BaseModel):
    success: bool
    dataset_id: str
    new_dataset_id: str = ""
    transforms_applied: int = 0
    rows_before: int = 0
    rows_after: int = 0
    columns_added: list[str] = Field(default_factory=list)
    columns_removed: list[str] = Field(default_factory=list)
    version: int = 0
    error: str | None = None


class ChatResponse(BaseModel):
    answer: str
    confidence: str = "medium"
    evidence: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


class ExportResponse(BaseModel):
    success: bool
    download_url: str = ""
    file_size: int = 0
    format: str = ""
    error: str | None = None
