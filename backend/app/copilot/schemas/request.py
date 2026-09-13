from pydantic import BaseModel, Field


class CopilotQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    session_id: str | None = None
    context: dict = Field(default_factory=dict)


class CopilotPlanRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    context: dict = Field(default_factory=dict)


class CopilotExecuteRequest(BaseModel):
    task_id: str
    step_id: str | None = None


class CopilotCancelRequest(BaseModel):
    task_id: str


class CopilotClarificationResponse(BaseModel):
    task_id: str
    clarification: str = Field(..., min_length=1)
