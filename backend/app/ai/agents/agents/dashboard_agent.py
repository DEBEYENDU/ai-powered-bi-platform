"""Dashboard Agent — generates dashboards, selects charts, creates layouts."""

from __future__ import annotations

from typing import Any

from app.ai.agents.agents.base import BaseAgent
from app.ai.agents.prompts.templates import DASHBOARD_AGENT_PROMPT


class DashboardAgent(BaseAgent):
    agent_type = "dashboard"
    name = "Dashboard Agent"
    description = "Generate dashboards, select charts, create layouts"

    CHART_TYPES = [
        "line",
        "bar",
        "pie",
        "doughnut",
        "area",
        "scatter",
        "heatmap",
        "treemap",
        "funnel",
        "gauge",
        "kpi_card",
        "table",
    ]

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
        tools: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data_summary = context.get("data_summary", "No data summary")
        chart_types = ", ".join(self.CHART_TYPES)

        prompt = DASHBOARD_AGENT_PROMPT.format(
            task=task,
            data_summary=data_summary,
            chart_types=chart_types,
        )

        llm_response = await self._call_llm(prompt)

        # Generate default dashboard config
        config = self._generate_config(context)

        return self._build_result(
            output=llm_response,
            data={
                "dashboard_config": config,
                "chart_recommendations": self._recommend_charts(context),
                "layout": self._default_layout(),
                "filters": self._suggest_filters(context),
            },
            artifacts=[{"type": "dashboard_config", "content": config}],
        )

    def _generate_config(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate a dashboard configuration."""
        data_cols = context.get("columns", [])
        return {
            "title": context.get("title", "Business Dashboard"),
            "layout": "grid",
            "columns": 12,
            "rows": "auto",
            "widgets": [
                {
                    "type": "kpi_card",
                    "title": "Key Metric",
                    "span": 3,
                    "data_binding": data_cols[0] if data_cols else "value",
                },
                {
                    "type": "line",
                    "title": "Trend Over Time",
                    "span": 8,
                    "data_binding": "time_series",
                },
                {
                    "type": "pie",
                    "title": "Distribution",
                    "span": 4,
                    "data_binding": "categories",
                },
            ],
        }

    def _recommend_charts(self, context: dict[str, Any]) -> list[dict[str, str]]:
        """Recommend chart types based on data characteristics."""
        recommendations: list[dict[str, str]] = [
            {"chart": "line", "use_case": "Time series trends"},
            {"chart": "bar", "use_case": "Category comparisons"},
            {"chart": "kpi_card", "use_case": "Key metrics display"},
            {"chart": "table", "use_case": "Detailed data lookup"},
        ]
        return recommendations

    def _default_layout(self) -> dict[str, Any]:
        return {
            "type": "grid",
            "columns": 12,
            "gap": 16,
            "responsive": {
                "lg": 12,
                "md": 8,
                "sm": 4,
            },
        }

    def _suggest_filters(self, context: dict[str, Any]) -> list[dict[str, str]]:
        """Suggest filter widgets."""
        return [
            {"type": "date_range", "label": "Date Range", "field": "date"},
            {"type": "dropdown", "label": "Category", "field": "category"},
        ]
