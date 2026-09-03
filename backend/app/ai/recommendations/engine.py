"""Recommendation Engine - actionable business recommendations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


class RecommendationEngine:
    """Generates prioritized actionable recommendations."""

    TEMPLATES = [
        ("Increase inventory", "Stock levels below optimal threshold", "medium"),
        ("Reduce stock", "Overstock detected in slow-moving items", "low"),
        ("Target customer segment", "High-value segment showing growth", "high"),
        ("Launch marketing campaign", "Underperforming region needs attention", "medium"),
        ("Adjust pricing", "Price elasticity suggests opportunity", "medium"),
        ("Investigate region", "Anomaly detected in regional performance", "high"),
        ("Review suppliers", "Supply variance affecting operations", "medium"),
        ("Retrain forecast model", "Model drift detected", "high"),
    ]

    def generate(
        self, context: str, category: Optional[str] = None, limit: int = 5
    ) -> Dict[str, Any]:
        recs = []
        for i, (title, desc, effort) in enumerate(self.TEMPLATES[:limit]):
            recs.append({
                "title": title,
                "description": f"{desc} (context: {context[:80]})",
                "expected_impact": "high" if i < 2 else "medium",
                "effort": effort,
                "confidence": round(0.9 - i * 0.05, 2),
                "actionable_steps": [
                    f"Step 1: Analyze {title.lower()} requirements",
                    f"Step 2: Execute {title.lower()} plan",
                ],
            })
        return {
            "recommendations": recs,
            "generated_at": datetime.utcnow().isoformat(),
            "context": context,
        }
