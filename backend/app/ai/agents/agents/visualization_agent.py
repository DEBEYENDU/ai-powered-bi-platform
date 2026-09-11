"""Visualization Agent — chart selection, UX improvement, drilldowns, responsive layouts."""

from __future__ import annotations

from typing import Any

from app.ai.agents.agents.base import BaseAgent
from app.ai.agents.prompts.templates import VISUALIZATION_AGENT_PROMPT


class VisualizationAgent(BaseAgent):
    agent_type = "visualization"
    name = "Visualization Agent"
    description = "Choose charts, improve UX, suggest drilldowns, responsive layouts"

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
        tools: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data_chars = context.get("data_characteristics", "No data info")
        existing = context.get("existing_charts", [])

        prompt = VISUALIZATION_AGENT_PROMPT.format(
            task=task,
            data_characteristics=data_chars,
            existing_charts=existing,
        )

        llm_response = await self._call_llm(prompt)

        recommendations = self._recommend_visualizations(context)

        return self._build_result(
            output=llm_response,
            data={
                "chart_recommendations": recommendations,
                "color_scheme": self._suggest_colors(context),
                "drilldown_suggestions": self._suggest_drilldowns(context),
                "responsive_config": self._responsive_config(),
                "accessibility": self._accessibility_checklist(),
            },
            artifacts=[{"type": "visualization_config", "content": recommendations}],
        )

    def _recommend_visualizations(self, context: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {"chart": "line", "rationale": "Best for showing trends over time"},
            {"chart": "bar", "rationale": "Best for comparing categories"},
            {"chart": "kpi_card", "rationale": "Best for displaying key metrics prominently"},
            {"chart": "table", "rationale": "Best for detailed data inspection"},
        ]

    def _suggest_colors(self, context: dict[str, Any]) -> dict[str, str]:
        return {
            "primary": "#1976d2",
            "secondary": "#dc004e",
            "success": "#4caf50",
            "warning": "#ff9800",
            "error": "#f44336",
            "background": "#ffffff",
            "text": "#212121",
        }

    def _suggest_drilldowns(self, context: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {"from": "summary", "to": "detail", "description": "Click to see individual records"},
            {"from": "monthly", "to": "daily", "description": "Drill down to daily granularity"},
        ]

    def _responsive_config(self) -> dict[str, Any]:
        return {
            "breakpoints": {"xs": 0, "sm": 600, "md": 960, "lg": 1280, "xl": 1920},
            "grid_columns": {"xs": 4, "sm": 8, "md": 12, "lg": 12},
            "widget_min_width": 280,
        }

    def _accessibility_checklist(self) -> list[str]:
        return [
            "Use sufficient color contrast (WCAG AA)",
            "Add alt text to all chart elements",
            "Ensure keyboard navigation works",
            "Use patterns/textures for colorblind users",
        ]
