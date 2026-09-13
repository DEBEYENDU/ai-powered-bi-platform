"""Dashboard planner - uses LLM to plan dashboard structure from natural language."""

from __future__ import annotations

import json
from typing import Any

from app.ai.providers.base import ChatMessage, LLMProvider

PLANNER_SYSTEM_PROMPT = """\
You are an expert BI dashboard architect. Given a natural language description,
plan a complete dashboard structure as JSON.

RULES:
1. Generate 4-12 widgets based on the request complexity.
2. Each widget must have: id, type, title, description, sql, chart, columns, reasoning.
3. Widget types must be one of: kpi, line, bar, area, pie, donut, scatter, heatmap, treemap, gauge, table, pivot, map, timeline, text, forecast.
4. Chart types: number, line, bar, area, pie, donut, scatter, heatmap, treemap, gauge, table, pivot, map, timeline, text, forecast.
5. Every SQL must be a valid PostgreSQL SELECT statement.
6. Include KPIs at the top, then charts, then tables.
7. Each widget needs a "reasoning" explaining why this chart was chosen.
8. Include filters relevant to the domain.
9. Return ONLY valid JSON, no markdown fences.

OUTPUT FORMAT:
{
  "title": "Dashboard Title",
  "description": "Brief description",
  "widgets": [
    {
      "id": "kpi_1",
      "type": "kpi",
      "title": "Total Revenue",
      "description": "Sum of all revenue",
      "sql": "SELECT SUM(amount) AS total_revenue FROM sales",
      "chart": "number",
      "columns": ["total_revenue"],
      "reasoning": "KPI card chosen for single key metric display"
    }
  ],
  "filters": [
    {"type": "date", "field": "created_at", "label": "Date Range"},
    {"type": "region", "field": "region", "label": "Region"}
  ],
  "theme": {"primary_color": "#1976d2", "accent_color": "#ff9800"}
}
"""

IMPROVE_SYSTEM_PROMPT = """\
You are an expert BI dashboard architect. Given an existing dashboard and an improvement instruction,
return the improved dashboard as JSON in the same format.

Analyze the current widgets and modify/add/remove based on the instruction.
Return ONLY valid JSON, no markdown fences.
"""


class DashboardPlanner:
    """Plans dashboard structure using LLM."""

    def __init__(self, provider: LLMProvider, model: str = "") -> None:
        self.provider = provider
        self.model = model or "gpt-4o-mini"

    async def plan(
        self,
        prompt: str,
        schema_text: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Plan a dashboard from a natural language prompt."""
        user_content = f"DATABASE SCHEMA:\n{schema_text}\n\nREQUEST: {prompt}"
        if schema_text:
            user_content = (
                f"DATABASE SCHEMA:\n{schema_text}\n\n"
                f"IMPORTANT: Only use tables and columns that exist in the schema above.\n\n"
                f"REQUEST: {prompt}"
            )

        messages = [
            ChatMessage(role="system", content=PLANNER_SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_content),
        ]

        response = await self.provider.chat(
            messages, model=self.model, temperature=temperature, max_tokens=max_tokens
        )

        return self._parse_json(response.content)

    async def improve(
        self,
        current_dashboard: dict[str, Any],
        instruction: str,
        schema_text: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Improve an existing dashboard based on instruction."""
        user_content = (
            f"DATABASE SCHEMA:\n{schema_text}\n\n"
            f"CURRENT DASHBOARD:\n{json.dumps(current_dashboard, indent=2)}\n\n"
            f"IMPROVEMENT INSTRUCTION: {instruction}"
        )

        messages = [
            ChatMessage(role="system", content=IMPROVE_SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_content),
        ]

        response = await self.provider.chat(
            messages, model=self.model, temperature=temperature, max_tokens=max_tokens
        )

        return self._parse_json(response.content)

    async def explain(
        self,
        widgets: list[dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> list[dict[str, Any]]:
        """Generate explanations for each widget."""
        system = (
            "You are a BI expert. For each widget, explain why it was created "
            "and what insights it provides. Return a JSON array of objects with "
            "'id' and 'explanation' fields. Return ONLY valid JSON."
        )
        user = f"WIDGETS:\n{json.dumps(widgets, indent=2)}"

        messages = [
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=user),
        ]

        response = await self.provider.chat(
            messages, model=self.model, temperature=temperature, max_tokens=max_tokens
        )

        parsed = self._parse_json(response.content)
        if isinstance(parsed, list):
            return parsed
        return parsed.get("explanations", [])

    def _parse_json(self, content: str) -> dict[str, Any]:
        """Parse JSON from LLM response, handling markdown fences."""
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            import re

            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group())
            match = re.search(r"\[.*\]", cleaned, re.DOTALL)
            if match:
                items = json.loads(match.group())
                return {"explanations": items}
            return {"title": "Untitled Dashboard", "widgets": [], "filters": [], "theme": {}}
