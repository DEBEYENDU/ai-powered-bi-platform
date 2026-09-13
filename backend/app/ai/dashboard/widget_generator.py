"""Widget generator - generates individual widgets with SQL and chart config."""

from __future__ import annotations

from typing import Any

from app.ai.providers.base import ChatMessage, LLMProvider

WIDGET_SYSTEM_PROMPT = """\
You are an expert SQL and data visualization engineer.
Given a widget specification, generate the optimal SQL query and chart configuration.

RULES:
1. Generate ONLY a valid PostgreSQL SELECT statement.
2. Use proper aggregations (SUM, COUNT, AVG, etc.).
3. Use meaningful column aliases.
4. Add ORDER BY and LIMIT as appropriate.
5. For time series, use DATE_TRUNC for proper grouping.
6. For KPIs, return a single row with the metric.
7. For charts, return grouped data suitable for visualization.
8. Return ONLY valid JSON.

OUTPUT FORMAT:
{
  "sql": "SELECT ...",
  "columns": ["label", "value"],
  "chart_config": {
    "type": "bar",
    "x_axis": "label",
    "y_axis": "value",
    "colors": ["#1976d2"]
  },
  "explanation": "This query aggregates..."
}
"""


class WidgetGenerator:
    """Generates widget SQL and configuration using LLM."""

    def __init__(self, provider: LLMProvider, model: str = "") -> None:
        self.provider = provider
        self.model = model or "gpt-4o-mini"

    async def generate_widget(
        self,
        widget_spec: dict[str, Any],
        schema_text: str,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Generate SQL and config for a single widget."""
        messages = [
            ChatMessage(role="system", content=WIDGET_SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=(
                    f"DATABASE SCHEMA:\n{schema_text}\n\n"
                    f"WIDGET SPECIFICATION:\n"
                    f"Type: {widget_spec.get('type', 'kpi')}\n"
                    f"Title: {widget_spec.get('title', '')}\n"
                    f"Description: {widget_spec.get('description', '')}\n"
                    f"Existing SQL hint: {widget_spec.get('sql', '')}\n\n"
                    f"Generate the optimal SQL and chart configuration."
                ),
            ),
        ]

        response = await self.provider.chat(
            messages, model=self.model, temperature=temperature, max_tokens=1024
        )

        import json
        import re

        content = response.strip() if hasattr(response, "strip") else response.content
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                result = json.loads(match.group())
            else:
                result = {
                    "sql": widget_spec.get("sql", "SELECT 1"),
                    "columns": [],
                    "chart_config": {"type": widget_spec.get("chart", "number")},
                    "explanation": "Generated from specification",
                }

        return result

    async def generate_widgets_batch(
        self,
        widgets: list[dict[str, Any]],
        schema_text: str,
        temperature: float = 0.2,
    ) -> list[dict[str, Any]]:
        """Generate SQL for multiple widgets."""
        results = []
        for widget in widgets:
            try:
                generated = await self.generate_widget(widget, schema_text, temperature)
                results.append(
                    {
                        **widget,
                        "sql": generated.get("sql", widget.get("sql", "")),
                        "columns": generated.get("columns", []),
                        "chart_config": generated.get("chart_config", {}),
                        "explanation": generated.get("explanation", widget.get("reasoning", "")),
                    }
                )
            except Exception:  # noqa: BLE001
                results.append(
                    {
                        **widget,
                        "sql_error": "Failed to generate SQL",
                    }
                )
        return results
