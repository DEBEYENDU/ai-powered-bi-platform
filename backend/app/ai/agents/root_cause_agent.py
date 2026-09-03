"""Root Cause Analysis Agent for AI Business Assistant."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RootCauseAgentConfig(BaseModel):
    name: str = "root_cause_agent"
    description: str = "Performs root cause analysis on business issues"
    model: str = "gpt-4"
    temperature: float = 0.2


class RootCauseAgent:
    """Agent specialized in root cause analysis."""

    def __init__(self, config: Optional[RootCauseAgentConfig] = None) -> None:
        self.config = config or RootCauseAgentConfig()
        self.name = self.config.name

    async def analyze_root_cause(
        self,
        issue: str,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        findings = self._identify_causes(issue, data)
        return {
            "agent": self.name,
            "issue": issue,
            "findings": findings,
            "confidence": self._calculate_confidence(findings),
            "methodology": "evidence_based_analysis",
        }

    def _identify_causes(self, issue: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings = []
        issue_lower = issue.lower()
        for key, value in data.items():
            if isinstance(value, (int, float)):
                findings.append({
                    "cause": f"Metric '{key}' may contribute to the issue",
                    "value": value,
                    "confidence": 0.6,
                })
        if not findings:
            findings.append({
                "cause": "Insufficient data for definitive root cause analysis",
                "confidence": 0.3,
            })
        return findings

    def _calculate_confidence(self, findings: List[Any]) -> float:
        if not findings:
            return 0.1
        avg = sum(f.get("confidence", 0.5) for f in findings) / len(findings)
        return min(1.0, avg)