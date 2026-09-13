from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    id: str
    tool: str
    purpose: str = ""
    params: dict = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    risk_level: str = "low"
    timeout_seconds: int = 120
    retry_on_failure: bool = False


class ExecutionPlan(BaseModel):
    goal: str
    steps: list[PlanStep]
    requires_clarification: bool = False
    clarification_question: str | None = None
    estimated_duration_ms: int = 0
    risk_assessment: str = "low"


class IntentResult(BaseModel):
    intent: str
    confidence: float
    entities: dict = Field(default_factory=dict)
    requires_clarification: bool = False
    clarification_question: str | None = None
