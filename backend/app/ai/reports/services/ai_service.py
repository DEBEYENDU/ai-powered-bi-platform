"""AI integration service — LLM calls for report generation."""

from __future__ import annotations

import json
from typing import Any

from app.ai.reports.prompts.templates import (
    REPORT_GENERATION_PROMPT,
    SECTION_PROMPTS,
    SYSTEM_PROMPT,
)


def _safe_json_parse(text: str) -> Any:
    """Extract JSON from LLM response, handling markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass
    return {}


def _safe_json_array(text: str) -> list[Any]:
    """Extract JSON array from LLM response."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines)
    try:
        result = json.loads(cleaned)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                result = json.loads(cleaned[start : end + 1])
                return result if isinstance(result, list) else []
            except json.JSONDecodeError:
                pass
    return []


class AIService:
    """Handles LLM interactions for report generation."""

    def __init__(self, provider: Any = None) -> None:
        self._provider = provider

    async def generate_report_content(
        self,
        prompt: str,
        report_type: str,
        data_context: str,
        kpis_context: str = "",
        chart_context: str = "",
        trend_context: str = "",
    ) -> dict[str, Any]:
        """Generate full report content via LLM."""
        if self._provider is None:
            return self._fallback_report(prompt, report_type, data_context)

        try:
            full_prompt = REPORT_GENERATION_PROMPT.format(
                prompt=prompt,
                report_type=report_type,
                data_context=data_context[:8000],
                kpis_context=kpis_context,
                chart_context=chart_context,
                trend_context=trend_context,
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt},
            ]
            response = await self._provider.chat(messages)
            content = response.get("content", "")
            parsed = _safe_json_parse(content)
            if isinstance(parsed, dict) and parsed.get("title"):
                return parsed
        except Exception:  # noqa: BLE001, S110
            pass

        return self._fallback_report(prompt, report_type, data_context)

    async def generate_section(
        self, section_type: str, data_context: str
    ) -> dict[str, Any]:
        """Generate a specific report section via LLM."""
        if self._provider is None:
            return {"title": section_type, "content": f"[Section: {section_type}]", "section_type": section_type}

        template = SECTION_PROMPTS.get(section_type, "")
        if not template:
            return {"title": section_type, "content": "", "section_type": section_type}

        try:
            prompt = template.format(data_context=data_context[:6000])
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            response = await self._provider.chat(messages)
            content = response.get("content", "")
            return {"title": section_type.replace("_", " ").title(), "content": content, "section_type": section_type}
        except Exception:  # noqa: BLE001
            return {"title": section_type, "content": "", "section_type": section_type}

    async def followup(self, report_context: str, question: str) -> str:
        """Answer a follow-up question about a report."""
        if self._provider is None:
            return "The AI service is not available to answer questions about this report."

        try:
            from app.ai.reports.prompts.templates import FOLLOWUP_PROMPT

            prompt = FOLLOWUP_PROMPT.format(report_context=report_context[:6000], question=question)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            response = await self._provider.chat(messages)
            return response.get("content", "I could not generate an answer.")
        except Exception as e:  # noqa: BLE001
            return f"Error generating response: {e}"

    def _fallback_report(
        self, prompt: str, report_type: str, data_context: str
    ) -> dict[str, Any]:
        """Generate a structured report without LLM."""
        return {
            "title": f"{report_type.title()} Report",
            "executive_summary": (
                f"This {report_type} report has been generated based on the provided data. "
                f"The analysis covers key metrics, trends, and recommendations."
            ),
            "sections": [
                {
                    "title": "Data Overview",
                    "content": f"Data context:\n{data_context[:2000]}",
                    "section_type": "analysis",
                },
                {
                    "title": "Analysis",
                    "content": f"Based on the prompt: {prompt}\nDetailed analysis of available data.",
                    "section_type": "analysis",
                },
            ],
            "kpis": [],
            "insights": [
                {
                    "title": "Data Review",
                    "description": "The data has been reviewed for key patterns.",
                    "insight_type": "observation",
                    "confidence": "medium",
                }
            ],
            "risks": [],
            "recommendations": [
                {
                    "title": "Connect Data Sources",
                    "description": "Connect more data sources for richer analysis.",
                    "priority": "medium",
                    "category": "operations",
                }
            ],
        }
