"""Executive Summary Agent for AI Business Assistant."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExecutiveSummaryAgentConfig(BaseModel):
    name: str = "executive_summary_agent"
    description: str = "Generates executive summaries"
    model: str = "gpt-4"
    temperature: float = 0.3


class ExecutiveSummaryAgent:
    """Agent specialized in executive summaries."""

    def __init__(self, config: Optional[ExecutiveSummaryAgentConfig] = None) -> None:
        self.config = config or ExecutiveSummaryAgentConfig()
        self.name = self.config.name

    async def generate_summary(
        self,
        data: Dict[str, Any],
        time_range: str,
        focus_areas: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        summary = self._generate_executive_summary(data, time_range, focus_areas)
        return {
            "agent": self.name,
            "time_range": time_range,
            "summary": summary,
            "key_insights": self._extract_key_insights(data),
            "recommendations": self._generate_recommendations(data),
        }

    def _generate_executive_summary(
        self, data: Dict[str, Any], time_range: str, focus_areas: Optional[List[str]]
    ) -> str:
        parts = [f"Executive Summary for {time_range}"]
        if focus_areas:
            parts.append(f"Focus areas: {', '.join(focus_areas)}")
        parts.append(f"Analyzed {len(data)} data points")
        return ". ".join(parts)

    def _extract_key_insights(self, data: Dict[str, Any]) -> List[str]:
        insights = []
        numeric = {k: v for k, v in data.items() if isinstance(v, (int, float))}
        if numeric:
            max_key = max(numeric, key=numeric.get)
            insights.append(f"Highest metric: {max_key}")
        return insights if insights else ["No specific insights"]

    def _generate_recommendations(self, data: Dict[str, Any]) -> List[str]:
        return [
            "Review key metrics for improvement opportunities",
            "Consider data-driven strategies based on trends",
        ]
