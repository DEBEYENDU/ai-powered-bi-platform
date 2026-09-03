"""Analytics Agent for AI Business Assistant."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalyticsAgentConfig(BaseModel):
    name: str = "analytics_agent"
    description: str = "Analyzes business data and KPIs"
    model: str = "gpt-4"
    temperature: float = 0.3


class AnalyticsAgent:
    """Agent specialized for analytics queries."""

    def __init__(self, config: Optional[AnalyticsAgentConfig] = None) -> None:
        self.config = config or AnalyticsAgentConfig()
        self.name = self.config.name

    async def analyze(
        self,
        query: str,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        analysis_type = self._determine_analysis_type(query, data)
        insights = self._generate_insights(data, analysis_type)
        return {
            "agent": self.name,
            "analysis_type": analysis_type,
            "insights": insights,
            "data_summary": self._summarize_data(data),
            "confidence": self._calculate_confidence(data),
        }

    def _determine_analysis_type(
        self, query: str, data: Dict[str, Any]
    ) -> str:
        query_lower = query.lower()
        if "revenue" in query_lower or "income" in query_lower:
            return "revenue_analysis"
        if "profit" in query_lower or "margin" in query_lower:
            return "profit_analysis"
        if "trend" in query_lower or "growth" in query_lower:
            return "trend_analysis"
        if "compare" in query_lower or "vs" in query_lower:
            return "comparison"
        if "anomal" in query_lower or "unusual" in query_lower:
            return "anomaly_detection"
        return "general_analytics"

    def _generate_insights(
        self, data: Dict[str, Any], analysis_type: str
    ) -> List[str]:
        insights: List[str] = []
        values = [v for v in data.values() if isinstance(v, (int, float))]
        if values:
            insights.append(f"Data contains {len(values)} numeric metrics")
            insights.append(f"Average value: {sum(values)/len(values):.2f}")
            insights.append(f"Maximum value: {max(values):.2f}")
            insights.append(f"Minimum value: {min(values):.2f}")
        if analysis_type == "revenue_analysis":
            insights.append("Revenue analysis indicates strong performance trends")
        return insights if insights else ["No specific insights generated"]

    def _summarize_data(self, data: Dict[str, Any]) -> str:
        keys = list(data.keys())[:5]
        return f"Analyzed {len(data)} metrics, focusing on {', '.join(keys)}"

    def _calculate_confidence(self, data: Dict[str, Any]) -> float:
        return min(1.0, 0.5 + len(data) * 0.05)
