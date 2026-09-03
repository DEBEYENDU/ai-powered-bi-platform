"""AI Tools module."""

from app.ai.tools.registry import ToolRegistry, ToolDefinition
from app.ai.tools.schemas import (
    NLQQuery, IntentDetection, KPICalculateRequest, KPICalculateResponse,
    RevenueAnalyticsRequest, RevenueAnalyticsResponse,
    SalesAnalyticsRequest, SalesAnalyticsResponse,
    GetDashboardRequest, GetDashboardResponse,
    GetDashboardSummaryRequest, GetDashboardSummaryResponse,
    ForecastRequest, ForecastResponse,
    GenerateReportRequest, GenerateReportResponse,
    ChatRequest, ChatResponse,
    RootCauseAnalysisRequest, RootCauseAnalysisResponse,
    RecommendationRequest, RecommendationResponse,
    ChartRequest, ChartResponse,
    Citation, CitationResponse,
)
from app.ai.tools.analytics_tools import (
    calculate_kpi_tool, revenue_analytics_tool, sales_analytics_tool,
)
from app.ai.tools.dashboard_tools import (
    get_dashboard_tool, get_dashboard_summary_tool,
)
from app.ai.tools.ml_tools import (
    run_forecast_tool, predict_tool,
)
from app.ai.tools.report_tools import (
    generate_report_tool, generate_executive_summary_tool,
)

__all__ = [
    "ToolRegistry", "ToolDefinition",
    "NLQQuery", "IntentDetection",
    "KPICalculateRequest", "KPICalculateResponse",
    "RevenueAnalyticsRequest", "RevenueAnalyticsResponse",
    "SalesAnalyticsRequest", "SalesAnalyticsResponse",
    "GetDashboardRequest", "GetDashboardResponse",
    "GetDashboardSummaryRequest", "GetDashboardSummaryResponse",
    "ForecastRequest", "ForecastResponse",
    "GenerateReportRequest", "GenerateReportResponse",
    "ChatRequest", "ChatResponse",
    "RootCauseAnalysisRequest", "RootCauseAnalysisResponse",
    "RecommendationRequest", "RecommendationResponse",
    "ChartRequest", "ChartResponse",
    "Citation", "CitationResponse",
    "calculate_kpi_tool", "revenue_analytics_tool", "sales_analytics_tool",
    "get_dashboard_tool", "get_dashboard_summary_tool",
    "run_forecast_tool", "predict_tool",
    "generate_report_tool", "generate_executive_summary_tool",
]
