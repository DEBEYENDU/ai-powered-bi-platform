"""Dashboard tool implementations for AI Business Assistant."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.ai.tools.schemas import (
    GetDashboardRequest,
    GetDashboardResponse,
    GetDashboardSummaryRequest,
    GetDashboardSummaryResponse,
)


def get_dashboard_tool(
    validated: BaseModel, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    if isinstance(validated, dict):
        validated = GetDashboardRequest(**validated)
    return GetDashboardResponse(
        dashboard_id=validated.dashboard_id,
        name="Executive Dashboard",
        widgets=[{"id": "w1", "type": "kpi_card", "title": "Revenue"}],
        kpis=[{"name": "revenue", "value": 1250000}],
        layout={},
    ).dict()


def get_dashboard_summary_tool(
    validated: BaseModel, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    if isinstance(validated, dict):
        validated = GetDashboardSummaryRequest(**validated)
    return GetDashboardSummaryResponse(
        dashboard_id=validated.dashboard_id,
        summary="Dashboard shows strong performance across all KPIs",
        key_insights=["Revenue up 12%", "Customer growth steady"],
        kpi_highlights=[{"kpi": "revenue", "value": 1250000}],
        recommended_actions=["Review monthly trends", "Investigate outliers"],
    ).dict()
