"""Data Quality Agent — detect issues and recommend cleaning."""

from __future__ import annotations

from typing import Any

from app.ai.agents.agents.base import BaseAgent
from app.ai.agents.prompts.templates import DATA_QUALITY_AGENT_PROMPT


class DataQualityAgent(BaseAgent):
    agent_type = "data_quality"
    name = "Data Quality Agent"
    description = "Detect missing values, duplicates, outliers, schema issues"

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
        tools: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data_profile = context.get("data_profile", "No profile")
        quality_score = context.get("quality_score", "N/A")

        prompt = DATA_QUALITY_AGENT_PROMPT.format(
            task=task,
            data_profile=data_profile,
            quality_score=quality_score,
        )

        llm_response = await self._call_llm(prompt)

        issues = self._detect_issues(context)

        return self._build_result(
            output=llm_response,
            data={
                "issues": issues,
                "quality_score": self._compute_score(issues),
                "cleaning_suggestions": self._suggest_cleaning(issues),
                "priority_fixes": self._prioritize_fixes(issues),
            },
            artifacts=[{"type": "quality_report", "content": issues}],
        )

    def _detect_issues(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect data quality issues from context."""
        issues: list[dict[str, Any]] = []
        profile = context.get("data_profile", {})
        if isinstance(profile, dict):
            for col, stats in profile.items():
                if isinstance(stats, dict):
                    null_pct = stats.get("null_pct", 0)
                    if null_pct > 5:
                        issues.append(
                            {
                                "column": col,
                                "type": "missing_values",
                                "severity": "high" if null_pct > 30 else "medium",
                                "description": f"{col}: {null_pct}% null values",
                            }
                        )
        if not issues:
            issues.append(
                {
                    "column": "_overall",
                    "type": "no_issues",
                    "severity": "info",
                    "description": "No significant quality issues detected",
                }
            )
        return issues

    def _compute_score(self, issues: list[dict[str, Any]]) -> float:
        if not issues or issues[0]["type"] == "no_issues":
            return 100.0
        deduction = sum({"high": 15, "medium": 8, "low": 3}.get(i["severity"], 2) for i in issues)
        return max(0, 100 - deduction)

    def _suggest_cleaning(self, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        suggestions: list[dict[str, Any]] = []
        for issue in issues:
            if issue["type"] == "missing_values":
                suggestions.append(
                    {
                        "column": issue["column"],
                        "action": "fill_missing",
                        "method": "median",
                        "description": f"Fill missing values in {issue['column']}",
                    }
                )
        return suggestions

    def _prioritize_fixes(self, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        sorted_issues = sorted(issues, key=lambda x: severity_order.get(x["severity"], 5))
        return sorted_issues[:5]
