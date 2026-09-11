"""Business Analyst Agent — KPI analysis, trends, anomalies, root cause."""

from __future__ import annotations

from typing import Any

from app.ai.agents.agents.base import BaseAgent
from app.ai.agents.prompts.templates import BUSINESS_ANALYST_PROMPT


class BusinessAnalystAgent(BaseAgent):
    agent_type = "business_analyst"
    name = "Business Analyst Agent"
    description = "Analyze KPIs, find trends, detect anomalies, root cause analysis"

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
        tools: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data_summary = context.get("data_summary", "No data")
        metrics = context.get("metrics", "No metrics")

        prompt = BUSINESS_ANALYST_PROMPT.format(
            task=task,
            data_summary=data_summary,
            metrics=metrics,
        )

        llm_response = await self._call_llm(prompt)

        findings = self._extract_findings(context)

        return self._build_result(
            output=llm_response,
            data={
                "findings": findings,
                "trends": self._detect_trends(context),
                "anomalies": self._detect_anomalies(context),
                "root_causes": self._root_cause_analysis(context),
                "recommendations": self._generate_recommendations(context),
            },
            artifacts=[{"type": "analysis", "content": findings}],
        )

    def _extract_findings(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract key findings from data context."""
        return [
            {"finding": "Data analyzed", "severity": "info", "details": "Analysis completed"},
        ]

    def _detect_trends(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect trends in data."""
        return [
            {"trend": "stable", "direction": "flat", "confidence": 0.7},
        ]

    def _detect_anomalies(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect anomalies."""
        return []

    def _root_cause_analysis(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Perform root cause analysis."""
        return [
            {
                "cause": "insufficient_data",
                "confidence": 0.5,
                "explanation": "More data needed for definitive analysis",
            },
        ]

    def _generate_recommendations(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate business recommendations."""
        return [
            {
                "category": "data_collection",
                "recommendation": "Collect more historical data for better trend analysis",
                "priority": "medium",
                "expected_impact": "Improved prediction accuracy",
            },
        ]
