"""Pydantic schemas for the Workflow Automation platform."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _id() -> str:
    return str(uuid.uuid4())[:12]


# --- Enums ---


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    FAILED = "failed"
    COMPLETED = "completed"


class TriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    CRON = "cron"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    DATASET_UPDATED = "dataset_updated"
    DASHBOARD_UPDATED = "dashboard_updated"
    REPORT_GENERATED = "report_generated"
    THRESHOLD_REACHED = "threshold_reached"
    ANOMALY_DETECTED = "anomaly_detected"
    FORECAST_RISK = "forecast_risk"
    WEBHOOK = "webhook"
    API = "api"


class ActionType(str, Enum):
    RUN_SQL = "run_sql"
    ANALYZE_DATASET = "analyze_dataset"
    GENERATE_DASHBOARD = "generate_dashboard"
    GENERATE_REPORT = "generate_report"
    GENERATE_FORECAST = "generate_forecast"
    RUN_AI_AGENT = "run_ai_agent"
    SEND_EMAIL = "send_email"
    SEND_NOTIFICATION = "send_notification"
    CREATE_ALERT = "create_alert"
    EXPORT_PDF = "export_pdf"
    EXPORT_EXCEL = "export_excel"
    EXPORT_POWERPOINT = "export_powerpoint"
    SAVE_FILE = "save_file"
    CALL_WEBHOOK = "call_webhook"
    RUN_PIPELINE = "run_pipeline"
    HUMAN_APPROVAL = "human_approval"
    EVALUATE_CONDITION = "evaluate_condition"
    KNOWLEDGE_SEARCH = "knowledge_search"
    RAG_QUERY = "rag_query"
    DOCUMENT_INGESTION = "document_ingestion"
    DOCUMENT_REINDEX = "document_reindex"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ConditionOperator(str, Enum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NEQ = "neq"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"


# --- Trigger Config ---


class TriggerConfig(BaseModel):
    type: TriggerType = TriggerType.MANUAL
    cron_expression: str = ""
    time: str = ""
    day_of_week: str = ""
    day_of_month: int = 0
    month: int = 0
    webhook_path: str = ""
    event_type: str = ""
    dataset_id: str = ""
    threshold_value: float = 0.0
    threshold_metric: str = ""


# --- Step Definition ---


class StepDefinition(BaseModel):
    id: str = Field(default_factory=_id)
    name: str = ""
    action_type: ActionType
    config: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    retry_on_failure: bool = True
    max_retries: int = 3
    timeout_seconds: int = 300
    continue_on_failure: bool = False
    is_approval_required: bool = False
    approval_assigned_to: str = ""
    fallback_step_id: str = ""
    parallel_group: str = ""


# --- Condition ---


class WorkflowCondition(BaseModel):
    id: str = Field(default_factory=_id)
    metric: str = ""
    operator: ConditionOperator = ConditionOperator.GT
    value: Any = None
    description: str = ""
    step_id: str = ""
    logical_op: str = "AND"


# --- Request Schemas ---


class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    trigger: TriggerConfig = Field(default_factory=TriggerConfig)
    steps: list[StepDefinition] = Field(default_factory=list)
    conditions: list[WorkflowCondition] = Field(default_factory=list)
    schedule: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    max_retries: int = 3
    timeout_seconds: int = 3600


class WorkflowUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    trigger: TriggerConfig | None = None
    steps: list[StepDefinition] | None = None
    conditions: list[WorkflowCondition] | None = None
    schedule: dict[str, Any] | None = None
    variables: dict[str, Any] | None = None
    tags: list[str] | None = None
    max_retries: int | None = None
    timeout_seconds: int | None = None


class WorkflowRunRequest(BaseModel):
    input_data: dict[str, Any] = Field(default_factory=dict)
    is_test: bool = False


class WorkflowAIRequest(BaseModel):
    prompt: str = Field(..., min_length=1)


class ApprovalRequest(BaseModel):
    status: ApprovalStatus
    response: str = ""


# --- Response Schemas ---


class WorkflowResponse(BaseModel):
    success: bool
    workflow_id: str = ""
    name: str = ""
    status: str = ""
    message: str = ""
    error: str | None = None


class WorkflowDetailResponse(BaseModel):
    success: bool
    id: str = ""
    name: str = ""
    description: str = ""
    status: str = ""
    trigger: dict[str, Any] = Field(default_factory=dict)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    schedule: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    max_retries: int = 3
    timeout_seconds: int = 3600
    last_run_at: str | None = None
    next_run_at: str | None = None
    created_at: str = ""
    updated_at: str = ""
    error: str | None = None


class WorkflowListResponse(BaseModel):
    success: bool
    workflows: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class ExecutionResponse(BaseModel):
    success: bool
    execution_id: str = ""
    workflow_id: str = ""
    status: str = ""
    message: str = ""
    error: str | None = None


class ExecutionDetailResponse(BaseModel):
    success: bool
    id: str = ""
    workflow_id: str = ""
    status: str = ""
    trigger_type: str = ""
    is_test: bool = False
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    steps: list[dict[str, Any]] = Field(default_factory=list)
    started_at: str = ""
    completed_at: str | None = None
    error: str | None = None


class ExecutionListResponse(BaseModel):
    success: bool
    executions: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class ApprovalResponse(BaseModel):
    success: bool
    approval_id: str = ""
    status: str = ""
    message: str = ""


class MonitoringStatsResponse(BaseModel):
    success: bool
    total_workflows: int = 0
    active_workflows: int = 0
    running_executions: int = 0
    completed_executions: int = 0
    failed_executions: int = 0
    avg_duration_ms: float = 0.0
    success_rate: float = 0.0
    upcoming_runs: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowLogResponse(BaseModel):
    success: bool
    logs: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class TemplateListResponse(BaseModel):
    success: bool
    templates: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class AIGenerateResponse(BaseModel):
    success: bool
    workflow: dict[str, Any] = Field(default_factory=dict)
    validation_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
