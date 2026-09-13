"""Request / response schemas for the AI Business Analyst."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InsightType(str, Enum):
    POSITIVE_TREND = "positive_trend"
    NEGATIVE_TREND = "negative_trend"
    HIGHEST_GROWTH = "highest_growth"
    LOWEST_GROWTH = "lowest_growth"
    TOP_PRODUCT = "top_product"
    WORST_PRODUCT = "worst_product"
    REGIONAL_COMPARISON = "regional_comparison"
    DEPARTMENT_COMPARISON = "department_comparison"
    CUSTOMER_SEGMENT = "customer_segment"
    SEASONALITY = "seasonality"


class AnomalyType(str, Enum):
    REVENUE_SPIKE = "revenue_spike"
    REVENUE_DROP = "revenue_drop"
    UNEXPECTED_SALES = "unexpected_sales"
    OUTLIER = "outlier"
    MISSING_VALUES = "missing_values"
    DUPLICATE_RECORDS = "duplicate_records"
    UNUSUAL_BEHAVIOR = "unusual_behavior"
    PERFORMANCE_DEGRADATION = "performance_degradation"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ComparisonPeriod(str, Enum):
    WOW = "week_over_week"
    MOM = "month_over_month"
    QOQ = "quarter_over_quarter"
    YOY = "year_over_year"


class SummaryType(str, Enum):
    BOARD = "board_meeting"
    CEO = "ceo"
    FINANCE = "finance"
    SALES = "sales"
    MARKETING = "marketing"
    OPERATIONS = "operations"
    EXECUTIVE_BRIEF = "executive_brief"


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    dashboard_id: str = Field(..., description="Dashboard to analyse")
    summary_type: SummaryType = Field(
        SummaryType.EXECUTIVE_BRIEF, description="Type of executive summary"
    )
    comparison: ComparisonPeriod | None = Field(
        None, description="Comparison period for trend analysis"
    )
    forecast_days: int = Field(30, ge=7, le=365, description="Forecast horizon in days")
    include_recommendations: bool = Field(True)
    include_anomalies: bool = Field(True)
    include_forecast: bool = Field(True)


class FollowUpRequest(BaseModel):
    dashboard_id: str
    question: str = Field(..., min_length=1)
    context: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Nested data
# ---------------------------------------------------------------------------


class Insight(BaseModel):
    id: str = ""
    type: InsightType
    title: str
    description: str
    evidence: list[str] = Field(default_factory=list)
    data_used: list[str] = Field(default_factory=list)
    business_logic: str = ""
    confidence: Confidence = Confidence.MEDIUM
    metric: str = ""
    current_value: float = 0.0
    previous_value: float | None = None
    change_pct: float = 0.0
    impact: str = ""


class Anomaly(BaseModel):
    id: str = ""
    type: AnomalyType
    title: str
    description: str
    severity: str = "medium"
    metric: str = ""
    expected_value: float = 0.0
    actual_value: float = 0.0
    deviation_pct: float = 0.0
    confidence: Confidence = Confidence.MEDIUM
    timestamp: str = ""
    evidence: list[str] = Field(default_factory=list)


class RootCause(BaseModel):
    factor: str
    contribution_pct: float = 0.0
    explanation: str = ""
    evidence: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    id: str = ""
    title: str
    description: str
    category: str = ""
    priority: str = "medium"
    expected_impact: str = ""
    evidence: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    business_logic: str = ""
    action_items: list[str] = Field(default_factory=list)


class ForecastPoint(BaseModel):
    date: str
    value: float
    lower_bound: float = 0.0
    upper_bound: float = 0.0


class Forecast(BaseModel):
    metric: str
    horizon_days: int
    points: list[ForecastPoint] = Field(default_factory=list)
    trend: str = ""
    seasonality_detected: bool = False
    confidence: Confidence = Confidence.MEDIUM
    accuracy_score: float = 0.0


class ChartExplanation(BaseModel):
    chart_id: str
    title: str
    meaning: str = ""
    action: str = ""
    importance: str = ""
    confidence: Confidence = Confidence.MEDIUM


class Summary(BaseModel):
    summary_type: SummaryType
    content: str
    key_metrics: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    generated_at: str = ""


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class AnalyzeResponse(BaseModel):
    success: bool
    dashboard_id: str
    summary: Summary | None = None
    insights: list[Insight] = Field(default_factory=list)
    anomalies: list[Anomaly] = Field(default_factory=list)
    root_causes: list[RootCause] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    forecast: Forecast | None = None
    chart_explanations: list[ChartExplanation] = Field(default_factory=list)
    risk_score: float = 0.0
    opportunity_score: float = 0.0
    analysis_time_ms: float = 0.0
    error: str | None = None


class FollowUpResponse(BaseModel):
    answer: str
    confidence: Confidence = Confidence.MEDIUM
    evidence: list[str] = Field(default_factory=list)
    related_insights: list[str] = Field(default_factory=list)
