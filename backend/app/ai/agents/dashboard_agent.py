"""Dashboard Agent for AI Business Assistant."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DashboardAgentConfig(BaseModel):
    name: str = "dashboard_agent"
    description: str = "Analyzes dashboards and visualizations"
    model: str = "gpt-4"
    temperature: float = 0.3


class DashboardAgent:
    """Agent specialized in dashboard analysis."""

    def __init__(self, config: Optional[DashboardAgentConfig] = None) -> None:
        self.config = config or DashboardAgentConfig()
        self.name = self.config.name

    async def analyze_dashboard(
        self,
        dashboard_data: Dict[str, Any],
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        widgets = dashboard_data.get("widgets", [])
        kpis = dashboard_data.get("kpis", [])
        insights = self._generate_dashboard_insights(
            widgets, kpis, query
        )
        return {
            "agent": self.name,
            "dashboard_name": dashboard_data.get("name", "Unknown"),
            "widget_count": len(widgets),
            "kpi_count": len(kpis),
            "insights": insights,
            "key_metrics": self._extract_key_metrics(dashboard_data),
        }

    def _generate_dashboard_insights(
        self, widgets: List, kpis: List, query: str
    ) -> List[str]:
        insights = []
        insights.append(f"Dashboard has {len(widgets)} widgets")
        insights.append(f"{len(kpis)} KPIs tracked")
        if "trend" in query.lower() or "insight" in query.lower():
            insights.append("Dashboard shows key performance trends")
        return insights

    def _extract_key_metrics(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            k: v for k, v in dashboard_data.items()
            if k not in ("widgets", "kpis", "name")
        }
