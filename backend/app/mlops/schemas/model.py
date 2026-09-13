"""Pydantic schemas for the MLOps lifecycle management system."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# --- Model Registry ---


class MLOpsModelCreate(BaseModel):
    name: str
    description: str = ""
    model_type: str
    task_type: str
    framework: str = "sklearn"
    tags: list[str] = Field(default_factory=list)


class MLOpsModelUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    model_type: str | None = None
    task_type: str | None = None
    framework: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class MLOpsModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    description: str
    model_type: str
    task_type: str
    framework: str
    owner_id: str
    status: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class MLOpsModelListResponse(BaseModel):
    data: list[MLOpsModelResponse]
    total: int


# --- Model Version ---


class MLOpsVersionCreate(BaseModel):
    artifact_path: str = ""
    framework: str = ""
    runtime_version: str = ""
    training_dataset_id: str = ""
    training_run_id: str | None = None
    feature_schema: dict[str, Any] = Field(default_factory=dict)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    created_by: str = ""


class MLOpsVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_id: str
    organization_id: str
    version: str
    version_number: int
    artifact_path: str
    checksum: str
    framework: str
    runtime_version: str
    training_dataset_id: str
    training_run_id: str | None
    feature_schema: dict[str, Any]
    hyperparameters: dict[str, Any]
    metrics: dict[str, Any]
    evaluation_id: str | None
    status: str
    is_active: bool
    created_by: str
    created_at: datetime


class MLOpsVersionCompareRequest(BaseModel):
    version_ids: list[str]


# --- Experiment ---


class MLOpsExperimentCreate(BaseModel):
    name: str
    description: str = ""
    objective: str = ""
    dataset_id: str = ""
    model_id: str | None = None


class MLOpsExperimentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    objective: str | None = None
    status: str | None = None


class MLOpsExperimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    description: str
    objective: str
    dataset_id: str
    model_id: str | None
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime


# --- Training Run ---


class MLOpsTrainingRequest(BaseModel):
    experiment_id: str | None = None
    model_id: str | None = None
    dataset_id: str
    target_column: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class MLOpsTrainingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    experiment_id: str
    model_id: str | None
    organization_id: str
    dataset_id: str
    target_column: str
    status: str
    parameters: dict[str, Any]
    metrics: dict[str, Any]
    artifact_path: str
    logs: str
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    created_by: str
    created_at: datetime


# --- Evaluation ---


class MLOpsEvaluationRequest(BaseModel):
    model_version_id: str
    dataset_id: str = ""
    dataset_name: str = ""
    evaluation_type: str = "test"


class MLOpsEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_version_id: str
    organization_id: str
    dataset_id: str
    dataset_name: str
    metrics: dict[str, Any]
    metric_definitions: dict[str, Any]
    evaluation_type: str
    sample_count: int
    evaluator_version: str
    created_at: datetime


class MLOpsModelComparisonResponse(BaseModel):
    versions: list[dict[str, Any]]
    best_version: str
    comparison_metric: str


# --- Deployment ---


class MLOpsDeploymentRequest(BaseModel):
    model_id: str
    model_version_id: str
    environment: str = "staging"
    config: dict[str, Any] = Field(default_factory=dict)


class MLOpsDeploymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_id: str
    model_version_id: str
    organization_id: str
    environment: str
    status: str
    endpoint: str
    health_status: str
    deployed_by: str
    deployed_at: datetime
    stopped_at: datetime | None
    config: dict[str, Any]
    traffic_percentage: float


class MLOpsPromotionRequest(BaseModel):
    target_environment: str = "production"


class MLOpsRollbackRequest(BaseModel):
    target_version_id: str


# --- Monitoring ---


class MLOpsMonitoringResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_id: str
    model_version_id: str | None
    organization_id: str
    metric_type: str
    metric_name: str
    metric_value: float
    dimensions: dict[str, Any]
    status: str
    message: str
    recorded_at: datetime


class MLOpsMonitoringSummary(BaseModel):
    model_id: str
    total_predictions: int = 0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    data_drift_score: float = 0.0
    prediction_drift_score: float = 0.0
    performance_score: float = 0.0


class MLOpsHealthResponse(BaseModel):
    model_id: str
    loaded: bool
    artifact_valid: bool
    current_version: str
    prediction_latency_ms: float
    recent_errors: int
    deployment_state: str


# --- Drift ---


class MLOpsDriftCheckRequest(BaseModel):
    model_id: str
    reference_dataset_id: str = ""
    current_dataset_id: str = ""


class MLOpsDriftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_id: str
    drift_type: str
    severity: str
    feature: str
    description: str
    metrics: dict[str, Any]
    recommended_action: str
    created_at: datetime


class MLOpsDriftStatus(BaseModel):
    status: str
    drifts: list[MLOpsDriftResponse]
    overall_health: str
    retraining_recommended: bool


# --- Common ---


class MLOpsErrorResponse(BaseModel):
    error: str
    detail: str = ""


class MLOpsSuccessResponse(BaseModel):
    success: bool
    message: str
