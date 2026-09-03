"""Pydantic schemas for AI Assistant tools."""

from __future__ import annotations

from typing import Any, List, Optional, Dict
from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID


# --- Query & Intent Schemas ---

class NLQQuery(BaseModel):
    """Natural Language Query request."""
    query: str = Field(..., description="The user's natural language question")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Optional context (organization, user preferences, etc.)"
    )
    include_chart: Optional[bool] = Field(
        False, description="Whether to generate a chart"
    )
    format: Optional[str] = Field(
        "text", description="Response format: text, table, chart"
    )


class IntentDetection(BaseModel):
    """Detected intent from user query."""
    intent: str = Field(..., description="Primary intent (e.g., 'kpi_query', 'forecast', 'dashboard_summary')")
    entities: Dict[str, Any] = Field(
        default_factory=dict, description="Extracted entities (KPI names, time ranges, dimensions)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score for the detected intent"
    )
    suggested_tools: List[str] = Field(
        default_factory=list, description="Suggested tool names"
    )


# --- KPI Tool Schemas ---

class KPICalculateRequest(BaseModel):
    """Request to calculate a KPI."""
    kpi: str = Field(..., description="KPI name (e.g., revenue, profit, roi)")
    dataset_id: UUID = Field(..., description="Target dataset UUID")
    start_date: Optional[datetime] = Field(None, description="Start of time range")
    end_date: Optional[datetime] = Field(None, description="End of time range")
    dimensions: Optional[List[str]] = Field(
        None, description="Dimension fields for breakdown (e.g., ['region', 'product'])"
    )
    
    @validator("kpi")
    def validate_kpi(cls, v: str) -> str:
        valid_kpis = [
            "revenue", "profit", "gross_margin", "net_margin", "roi",
            "roas", "average_order_value", "sales_growth", "customer_growth",
            "customer_retention", "churn", "inventory_turnover", "conversion_rate",
            "customer_lifetime_value", "employee_productivity"
        ]
        if v.lower() not in valid_kpis:
            raise ValueError(f"Invalid KPI. Must be one of: {', '.join(valid_kpis)}")
        return v.lower()


class KPICalculateResponse(BaseModel):
    """Response from KPI calculation."""
    kpi: str
    value: float
    unit: str
    currency: Optional[str] = Field(None, description="Currency if applicable")
    dataset_id: UUID
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    timestamp: datetime
    breakdown: Optional[Dict[str, Any]] = Field(None, description="Breakdown by dimensions")


# --- Analytics Tool Schemas ---

class RevenueAnalyticsRequest(BaseModel):
    """Request for revenue analytics."""
    dataset_id: UUID = Field(..., description="Target dataset UUID")
    start_date: Optional[datetime] = Field(None, description="Start of time range")
    end_date: Optional[datetime] = Field(None, description="End of time range")
    dimensions: Optional[List[str]] = Field(
        None, description="Dimension fields for breakdown"
    )
    metrics: Optional[List[str]] = Field(
        None, description="Specific metrics to include"
    )
    granularity: Optional[str] = Field(
        "auto", description="Time granularity (auto, daily, weekly, monthly, quarterly, yearly)"
    )


class RevenueAnalyticsResponse(BaseModel):
    """Response from revenue analytics."""
    dataset_id: UUID
    period: Optional[str]
    total_revenue: float
    revenue_by_dimension: Dict[str, Any]
    trend: Optional[str] = Field(None, description="Trend direction (up, down, stable)")
    growth_rate: Optional[float] = Field(None, description="Percentage growth")
    top_contributors: Optional[List[Dict[str, Any]]] = Field(
        None, description="Top contributing entities"
    )


class SalesAnalyticsRequest(BaseModel):
    """Request for sales analytics."""
    dataset_id: UUID = Field(..., description="Target dataset UUID")
    start_date: Optional[datetime] = Field(None, description="Start of time range")
    end_date: Optional[datetime] = Field(None, description="End of time range")
    dimensions: Optional[List[str]] = Field(
        None, description="Dimension fields for breakdown"
    )


class SalesAnalyticsResponse(BaseModel):
    """Response from sales analytics."""
    dataset_id: UUID
    total_sales: float
    number_of_transactions: int
    average_transaction_value: float
    sales_by_dimension: Dict[str, Any]
    trend: Optional[str]
    growth_rate: Optional[float]


# --- Dashboard Tool Schemas ---

class GetDashboardRequest(BaseModel):
    """Request to retrieve a dashboard."""
    dashboard_id: UUID = Field(..., description="Dashboard UUID")
    include_widgets: bool = Field(
        True, description="Whether to include widget data"
    )


class GetDashboardResponse(BaseModel):
    """Response from dashboard retrieval."""
    dashboard_id: UUID
    name: str
    description: Optional[str]
    widgets: List[Dict[str, Any]]
    kpis: List[Dict[str, Any]]
    layout: Dict[str, Any]


class GetDashboardSummaryRequest(BaseModel):
    """Request for dashboard summary."""
    dashboard_id: UUID = Field(..., description="Dashboard UUID")
    focus_areas: Optional[List[str]] = Field(
        None, description="Areas to focus summary on"
    )


class GetDashboardSummaryResponse(BaseModel):
    """Response from dashboard summary."""
    dashboard_id: UUID
    summary: str
    key_insights: List[str]
    kpi_highlights: List[Dict[str, Any]]
    recommended_actions: List[str]


# --- ML/Forecast Tool Schemas ---

class ForecastRequest(BaseModel):
    """Request to run a forecast."""
    kpi: str = Field(..., description="KPI to forecast (e.g., revenue, sales)")
    dataset_id: UUID = Field(..., description="Target dataset UUID")
    horizon: int = Field(
        ..., description="Forecast horizon (e.g., 30 for next 30 days)"
    )
    model_type: Optional[str] = Field(
        "auto", description="Model type (auto, arima, exponential_smoothing, prophet)"
    )
    include_confidence: bool = Field(
        True, description="Whether to include confidence intervals"
    )


class ForecastResponse(BaseModel):
    """Response from forecast execution."""
    kpi: str
    horizon: int
    forecast_values: List[float]
    confidence_intervals: Optional[Dict[str, Any]] = Field(None, description="Confidence intervals")
    model_type: str
    trained_at: datetime
    accuracy: Optional[float] = Field(None, description="Model accuracy if available")


# --- Report Tool Schemas ---

class GenerateReportRequest(BaseModel):
    """Request to generate a report."""
    report_type: str = Field(
        ..., description="Report type (executive, department, sales, financial, etc.)"
    )
    dataset_id: Optional[UUID] = Field(None, description="Target dataset UUID")
    time_range: Optional[str] = Field(
        "last_30_days", description="Time range for report"
    )
    include_recommendations: bool = Field(
        True, description="Whether to include AI recommendations"
    )
    format: Optional[str] = Field(
        "pdf", description="Output format (pdf, html, csv, json)"
    )


class GenerateReportResponse(BaseModel):
    """Response from report generation."""
    report_id: UUID
    report_type: str
    dataset_id: Optional[UUID]
    format: str
    generated_at: datetime
    download_url: Optional[str] = Field(None, description="URL to download report")
    executive_summary: Optional[str] = Field(None, description="AI-generated executive summary")


# --- Chat/Conversation Schemas ---

class ChatMessage(BaseModel):
    """Individual chat message."""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    citations: Optional[List[Dict[str, Any]]] = Field(
        None, description="Supporting citations"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata (tool calls, etc.)"
    )


class ChatRequest(BaseModel):
    """Chat conversation request."""
    message: str = Field(..., description="User's message")
    conversation_id: Optional[UUID] = Field(
        None, description="Existing conversation ID"
    )
    session_id: Optional[UUID] = Field(
        None, description="Session ID for new conversations"
    )
    include_memory: bool = Field(
        True, description="Whether to include conversation history"
    )


class ChatResponse(BaseModel):
    """Chat conversation response."""
    response: str
    conversation_id: UUID
    message: ChatMessage
    citations: List[Dict[str, Any]]
    suggested_questions: List[str]
    intent: IntentDetection
    execution_summary: Optional[Dict[str, Any]] = Field(
        None, description="Summary of tool executions"
    )


# --- Root Cause Analysis Schemas ---

class RootCauseAnalysisRequest(BaseModel):
    """Request for root cause analysis."""
    issue: str = Field(..., description="The business issue to analyze (e.g., 'revenue decline', 'customer churn')")
    dataset_id: UUID = Field(..., description="Dataset to analyze")
    time_range: Optional[str] = Field(
        "last_quarter", description="Time range for analysis"
    )
    dimensions: Optional[List[str]] = Field(
        None, description="Dimension fields to investigate"
    )


class RootCauseFinding(BaseModel):
    """A single root cause finding."""
    cause: str
    evidence: List[Dict[str, Any]]
    impact: Optional[str] = Field(None, description="Estimated impact")
    confidence: float = Field(ge=0.0, le=1.0)
    recommendation: str


class RootCauseAnalysisResponse(BaseModel):
    """Response from root cause analysis."""
    issue: str
    findings: List[RootCauseFinding]
    overall_assessment: str
    recommended_actions: List[str]


# --- Recommendation Schemas ---

class RecommendationRequest(BaseModel):
    """Request for recommendations."""
    context: str = Field(..., description="Business context for recommendations")
    category: Optional[str] = Field(
        None, description="Category (inventory, marketing, pricing, operations, etc.)"
    )
    limit: Optional[int] = Field(
        5, description="Maximum number of recommendations"
    )


class Recommendation(BaseModel):
    """A single recommendation."""
    title: str
    description: str
    expected_impact: Optional[str] = Field(None, description="Expected impact description")
    effort: Optional[str] = Field(None, description="Implementation effort (low, medium, high)")
    confidence: float = Field(ge=0.0, le=1.0)
    actionable_steps: List[str]


class RecommendationResponse(BaseModel):
    """Response from recommendation engine."""
    recommendations: List[Recommendation]
    generated_at: datetime
    context: str


# --- Chart Generation Schemas ---

class ChartConfig(BaseModel):
    """Configuration for chart generation."""
    chart_type: str = Field(
        ..., description="Chart type (line, bar, pie, scatter, heatmap, treemap, waterfall, gauge, timeline)"
    )
    title: Optional[str] = Field(None, description="Chart title")
    x_axis: Optional[str] = Field(None, description="X-axis field")
    y_axis: Optional[str] = Field(None, description="Y-axis field")
    dimensions: Optional[List[str]] = Field(
        None, description="Additional dimension fields"
    )
    filters: Optional[Dict[str, Any]] = Field(
        None, description="Filter criteria"
    )
    width: Optional[int] = Field(None, description="Chart width in pixels")
    height: Optional[int] = Field(None, description="Chart height in pixels")


class ChartRequest(BaseModel):
    """Request for chart generation."""
    config: ChartConfig


class ChartResponse(BaseModel):
    """Response from chart generation."""
    chart_id: str
    chart_type: str
    config: ChartConfig
    image_url: Optional[str] = Field(None, description="URL to rendered chart image")
    svg: Optional[str] = Field(None, description="SVG representation")


# --- Citation Schemas ---

class Citation(BaseModel):
    """A citation supporting an AI response claim."""
    source: str = Field(..., description="Source identifier (dataset, dashboard, document)")
    source_type: str = Field(
        ..., description="Type of source (dataset, dashboard, kpi, report, document)"
    )
    source_id: UUID = Field(..., description="Source UUID")
    snippet: str = Field(..., description="Relevant text snippet")
    relevance_score: float = Field(
        ge=0.0, le=1.0, description="How relevant this snippet is to the claim"
    )
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


class CitationRequest(BaseModel):
    """Request for citation generation."""
    claim: str = Field(..., description="The claim to cite sources for")
    conversation_id: UUID = Field(..., description="Conversation identifier")


class CitationResponse(BaseModel):
    """Response from citation generation."""
    citations: List[Citation]
    confidence_score: float
    evidence_strength: str  # "strong", "moderate", "weak"


# --- PII Detection Schemas ---

class PIIDetectionResult(BaseModel):
    """Result of PII detection."""
    has_pii: bool
    pii_types: List[str] = Field(
        default_factory=list, description="Detected PII types (email, ssn, credit_card, etc.)"
    )
    masked_text: str = Field(
        ..., description="Text with PII masked"
    )
    risk_level: str = Field(
        ..., description="Risk level (low, medium, high)"
    )