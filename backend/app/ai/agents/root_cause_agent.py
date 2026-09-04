"""Root Cause Analysis Agent for AI Business Assistant."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RootCauseAgentConfig(BaseModel):
    name: str = "root_cause_agent"
    description: str = "Performs root cause analysis on business issues"
    model: str = "gpt-4"
    temperature: float = 0.2


class RootCauseAgent:
    """Agent specialized in root cause analysis."""

    def __init__(self, config: RootCauseAgentConfig | None = None) -> None:
        self.config = config or RootCauseAgentConfig()
        self.name = self.config.name

    async def analyze_root_cause(
        self,
        issue: str,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        findings = self._identify_causes(issue, data)
        return {
            "agent": self.name,
            "issue": issue,
            "findings": findings,
            "confidence": self._calculate_confidence(findings),
            "methodology": "evidence_based_analysis",
        }

    def _identify_causes(self, issue: str, data: dict[str, Any]) -> list[dict[str, Any]]:
        findings = []
        for key, value in data.items():
            if isinstance(value, (int, float)):
                findings.append(
                    {
                        "cause": f"Metric '{key}' may contribute to the issue",
                        "value": value,
                        "confidence": 0.6,
                    }
                )
        if not findings:
            findings.append(
                {
                    "cause": "Insufficient data for definitive root cause analysis",
                    "confidence": 0.3,
                }
            )
        return findings

    def _calculate_confidence(self, findings: list[Any]) -> float:
        if not findings:
            return 0.1
        avg = sum(f.get("confidence", 0.5) for f in findings) / len(findings)
        return min(1.0, avg)
