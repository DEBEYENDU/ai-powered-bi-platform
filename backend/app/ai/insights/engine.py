"""Business Insights Engine - deterministic rules before LLM reasoning."""

from __future__ import annotations

from typing import Any


class InsightsEngine:
    """Generates deterministic business insights."""

    def generate(self, category: str, data: dict[str, Any]) -> dict[str, Any]:
        numeric = {k: v for k, v in data.items() if isinstance(v, (int, float))}
        insights: list[str] = []
        if numeric:
            total = sum(numeric.values())
            avg = total / len(numeric)
            mx = max(numeric, key=numeric.get)
            mn = min(numeric, key=numeric.get)
            insights.append(f"{category} total is {total:.2f} across {len(numeric)} metrics")
            insights.append(f"Average {category} metric is {avg:.2f}")
            insights.append(f"Top contributor: {mx} ({numeric[mx]:.2f})")
            insights.append(f"Lowest contributor: {mn} ({numeric[mn]:.2f})")
        else:
            insights.append(f"No numeric data available for {category} insights")
        return {
            "category": category,
            "insights": insights,
            "trend": self._detect_trend(numeric),
            "confidence": 0.8 if numeric else 0.2,
        }

    def _detect_trend(self, numeric: dict[str, float]) -> str:
        vals = list(numeric.values())
        if len(vals) < 2:
            return "insufficient_data"
        if vals[-1] > vals[0]:
            return "upward"
        if vals[-1] < vals[0]:
            return "downward"
        return "stable"
