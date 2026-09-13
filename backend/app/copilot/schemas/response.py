from pydantic import BaseModel, Field


class CopilotStepResult(BaseModel):
    step_id: str
    tool_name: str
    purpose: str
    status: str
    result: dict | None = None
    error: str | None = None
    duration_ms: float | None = None


class CopilotTaskResponse(BaseModel):
    task_id: str
    session_id: str
    status: str
    request: str
    intent: str | None = None
    intent_confidence: float | None = None
    steps: list[CopilotStepResult] = Field(default_factory=list)
    answer: str | None = None
    answer_parts: list[dict] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    total_steps: int = 0
    completed_steps: int = 0
    error: str | None = None
    created_at: str | None = None
    completed_at: str | None = None


class CopilotSessionResponse(BaseModel):
    id: str
    title: str | None = None
    message_count: int = 0
    created_at: str | None = None


class CopilotSessionListResponse(BaseModel):
    data: list[CopilotSessionResponse]
    total: int
