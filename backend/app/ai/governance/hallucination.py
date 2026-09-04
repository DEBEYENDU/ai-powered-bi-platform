"""Hallucination detection and mitigation for AI Business Assistant."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HallucinationRisk(BaseModel):
    tool_name: str
    risk_level: str = Field(..., description="Risk level (low, medium, high)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    evidence_present: bool = Field(False, description="Whether evidence is present")
    reason: str = Field(..., description="Reason for risk level")


class HallucinationDetector:
    """Validates AI outputs to prevent hallucinations."""

    def validate(self, execution_results: list[Any]) -> dict[str, Any]:
        risks: list[HallucinationRisk] = []
        total_risk_score = 0.0

        for result in execution_results:
            if not result.success:
                risks.append(
                    HallucinationRisk(
                        tool_name=result.tool_name,
                        risk_level="high",
                        confidence=0.0,
                        evidence_present=False,
                        reason="Tool execution failed",
                    )
                )
                total_risk_score += 1.0
                continue

            data = result.data if hasattr(result, "data") and result.data is not None else None
            if data is None:
                risks.append(
                    HallucinationRisk(
                        tool_name=result.tool_name,
                        risk_level="medium",
                        confidence=0.5,
                        evidence_present=False,
                        reason="No data returned from tool",
                    )
                )
                total_risk_score += 0.5
                continue

            evidence_score = self._assess_evidence(data)
            risks.append(
                HallucinationRisk(
                    tool_name=result.tool_name,
                    risk_level="low"
                    if evidence_score > 0.7
                    else "medium"
                    if evidence_score > 0.4
                    else "high",
                    confidence=evidence_score,
                    evidence_present=evidence_score > 0.5,
                    reason=f"Evidence confidence: {evidence_score:.2f}",
                )
            )
            total_risk_score += 1.0 - evidence_score

        overall_risk = min(1.0, total_risk_score / max(len(execution_results), 1))

        return {
            "hallucination_detected": overall_risk > 0.7,
            "overall_risk_score": round(overall_risk, 4),
            "risks": [r.dict() for r in risks],
            "recommendation": self._get_recommendation(overall_risk, risks),
        }

    def _assess_evidence(self, data: Any) -> float:
        if isinstance(data, dict):
            if not data:
                return 0.0
            has_data_fields = any(
                k in data for k in ["values", "metrics", "summary", "results", "data", "findings"]
            )
            if has_data_fields:
                return 0.85
            return 0.5
        if isinstance(data, (list, tuple)):
            return 0.8 if len(data) > 0 else 0.1
        if isinstance(data, str):
            if len(data.strip()) > 10:
                return 0.6
            return 0.3
        return 0.5

    def _get_recommendation(self, risk: float, risks: list[HallucinationRisk]) -> str:
        if risk > 0.7:
            return "High hallucination risk. Fall back to data-driven response and flag for review."
        if risk > 0.4:
            return "Moderate risk. Include citations and confidence scores."
        return "Low risk. Response appears grounded in retrieved data."
