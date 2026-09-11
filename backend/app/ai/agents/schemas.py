"""Request / response schemas for the Multi-Agent platform."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _id() -> str:
    return str(uuid.uuid4())[:12]


class AgentType(str, Enum):
    SQL = "sql"
    DASHBOARD = "dashboard"
    BUSINESS_ANALYST = "business_analyst"
    FORECAST = "forecast"
    REPORT = "report"
    DATA_QUALITY = "data_quality"
    SECURITY = "security"
    WORKFLOW = "workflow"
    KNOWLEDGE = "knowledge"
    VISUALIZATION = "visualization"
    COORDINATOR = "coordinator"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MessageType(str, Enum):
    DELEGATE = "delegate"
    RESULT = "result"
    CLARIFICATION = "clarification"
    CONTEXT = "context"
    ERROR = "error"
    RETRY = "retry"


# --- Request schemas ---


class AgentRunRequest(BaseModel):
    task: str = Field(..., min_length=1, description="Natural language task description")
    context: dict[str, Any] = Field(default_factory=dict)
    session_id: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    max_retries: int = 2
    timeout_seconds: int = 300


class AgentMessage(BaseModel):
    id: str = Field(default_factory=_id)
    from_agent: str
    to_agent: str
    message_type: MessageType
    content: dict[str, Any] = Field(default_factory=dict)
    task_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class TaskStep(BaseModel):
    step_id: str = Field(default_factory=_id)
    agent_type: str
    description: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    started_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0.0
    error: str | None = None
    retries: int = 0


# --- Nested models ---


class AgentStatus(BaseModel):
    agent_type: str
    name: str
    status: str  # ready, busy, error
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_duration_ms: float = 0.0
    last_active: str = ""


class ExecutionPlan(BaseModel):
    task_id: str = Field(default_factory=_id)
    original_task: str
    decomposed_steps: list[TaskStep] = Field(default_factory=list)
    agent_sequence: list[str] = Field(default_factory=list)
    estimated_duration_ms: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class MemoryEntry(BaseModel):
    id: str = Field(default_factory=_id)
    memory_type: str  # conversation, session, task, shared, vector
    key: str
    value: Any
    agent_type: str = ""
    task_id: str = ""
    session_id: str = ""
    embedding: list[float] | None = None
    expires_at: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ToolDefinition(BaseModel):
    name: str
    description: str
    agent_types: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ExecutionMetrics(BaseModel):
    task_id: str = ""
    total_duration_ms: float = 0.0
    agents_called: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    failures: int = 0
    retries: int = 0
    steps: list[TaskStep] = Field(default_factory=list)


class AgentLog(BaseModel):
    id: str = Field(default_factory=_id)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    level: str = "info"
    agent_type: str = ""
    task_id: str = ""
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


# --- Response schemas ---


class AgentRunResponse(BaseModel):
    success: bool
    task_id: str = ""
    answer: str = ""
    agent_sequence: list[str] = Field(default_factory=list)
    steps: list[TaskStep] = Field(default_factory=list)
    metrics: ExecutionMetrics = Field(default_factory=ExecutionMetrics)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class AgentListResponse(BaseModel):
    success: bool
    agents: list[AgentStatus] = Field(default_factory=list)
    count: int = 0


class TaskHistoryResponse(BaseModel):
    success: bool
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class LogsResponse(BaseModel):
    success: bool
    logs: list[AgentLog] = Field(default_factory=list)
    count: int = 0


class MemoryResponse(BaseModel):
    success: bool
    entries: list[MemoryEntry] = Field(default_factory=list)
    count: int = 0
