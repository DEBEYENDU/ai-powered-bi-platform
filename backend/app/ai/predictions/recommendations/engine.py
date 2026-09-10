"""Business recommendations engine — generates actionable recommendations
from prediction results, feature importances, and trend analysis."""

from __future__ import annotations

from typing import Any

import numpy as np


def generate_recommendations(
    target: str,
    predictions: list[dict[str, Any]],
    feature_importances: list[dict[str, Any]],
    trend: str,
    growth_pct: float,
    risk_score: float,
    metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate business recommendations from prediction analysis."""
    recommendations: list[dict[str, Any]] = []

    # --- Trend-based recommendations ---
    if trend == "increasing" and growth_pct > 5:
        recommendations.append({
            "category": "growth",
            "recommendation": f"{target} is projected to grow {growth_pct:.1f}%. Consider scaling operations to meet increased demand.",
            "impact": f"Potential {growth_pct:.1f}% increase in {target}",
            "priority": "high" if growth_pct > 20 else "medium",
            "confidence": "high" if metrics.get("r2", 0) > 0.7 else "medium",
        })
    elif trend == "decreasing" and growth_pct < -5:
        recommendations.append({
            "category": "risk_mitigation",
            "recommendation": f"{target} is projected to decline {abs(growth_pct):.1f}%. Investigate root causes and implement corrective measures.",
            "impact": f"Potential {abs(growth_pct):.1f}% decrease in {target}",
            "priority": "critical" if growth_pct < -20 else "high",
            "confidence": "high" if metrics.get("r2", 0) > 0.7 else "medium",
        })

    # --- Risk-based recommendations ---
    if risk_score > 70:
        recommendations.append({
            "category": "risk_management",
            "recommendation": f"High risk score ({risk_score}/100) detected. Develop contingency plans and monitor closely.",
            "impact": "Reduced exposure to potential losses",
            "priority": "critical",
            "confidence": "high",
        })
    elif risk_score > 40:
        recommendations.append({
            "category": "risk_management",
            "recommendation": f"Moderate risk score ({risk_score}/100). Consider risk mitigation strategies.",
            "impact": "Improved risk posture",
            "priority": "medium",
            "confidence": "medium",
        })

    # --- Feature-based recommendations ---
    if feature_importances:
        top_feature = feature_importances[0]
        second_feature = feature_importances[1] if len(feature_importances) > 1 else None

        recommendations.append({
            "category": "optimization",
            "recommendation": f"Focus on '{top_feature['feature']}' — it has the highest impact ({top_feature['importance']:.1%}) on {target}.",
            "impact": "Leveraging top driver for maximum impact",
            "priority": "high",
            "confidence": "high",
        })

        if second_feature:
            recommendations.append({
                "category": "optimization",
                "recommendation": f"Also prioritize '{second_feature['feature']}' ({second_feature['importance']:.1%} impact).",
                "impact": "Secondary optimization opportunity",
                "priority": "medium",
                "confidence": "medium",
            })

    # --- Model performance recommendations ---
    r2 = metrics.get("r2", metrics.get("roc_auc", 0))
    if r2 > 0.8:
        recommendations.append({
            "category": "model_confidence",
            "recommendation": f"High model accuracy ({r2:.1%}). Forecasts can be used for strategic planning.",
            "impact": "Confident decision-making",
            "priority": "low",
            "confidence": "high",
        })
    elif r2 < 0.5:
        recommendations.append({
            "category": "model_improvement",
            "recommendation": f"Model accuracy is {r2:.1%}. Consider adding features, collecting more data, or trying alternative models.",
            "impact": "Improved prediction accuracy",
            "priority": "medium",
            "confidence": "medium",
        })

    # --- Volatility recommendations ---
    if len(predictions) >= 7:
        values = [p["value"] for p in predictions]
        cv = np.std(values) / max(abs(np.mean(values)), 1e-10)
        if cv > 0.3:
            recommendations.append({
                "category": "volatility",
                "recommendation": f"High volatility detected (CV={cv:.2f}). Consider hedging or building reserves.",
                "impact": "Reduced impact of fluctuations",
                "priority": "medium",
                "confidence": "medium",
            })

    # --- Confidence interval recommendations ---
    if predictions:
        avg_width = np.mean([
            p.get("upper_bound", p["value"]) - p.get("lower_bound", p["value"])
            for p in predictions
        ])
        avg_val = np.mean([p["value"] for p in predictions])
        if avg_val != 0 and avg_width / abs(avg_val) > 0.5:
            recommendations.append({
                "category": "uncertainty",
                "recommendation": "Wide confidence intervals suggest high uncertainty. Consider scenario planning.",
                "impact": "Better preparedness for range of outcomes",
                "priority": "medium",
                "confidence": "high",
            })

    # Always add an action item
    if not recommendations or recommendations[-1]["category"] != "action":
        recommendations.append({
            "category": "action",
            "recommendation": f"Review this {target} forecast regularly and update the model as new data becomes available.",
            "impact": "Continuously improving accuracy",
            "priority": "low",
            "confidence": "high",
        })

    return recommendations


def assess_risk(
    predictions: list[dict[str, Any]],
    trend: str,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """Assess overall risk score for a prediction."""
    risk_factors: list[dict[str, Any]] = []

    # Trend risk
    if trend == "decreasing":
        risk_factors.append({"factor": "declining_trend", "score": 60, "explanation": "Downward trend detected"})
    elif trend == "volatile":
        risk_factors.append({"factor": "volatility", "score": 70, "explanation": "High volatility in predictions"})
    else:
        risk_factors.append({"factor": "trend", "score": 20, "explanation": "Stable/increasing trend"})

    # Model confidence risk
    r2 = metrics.get("r2", metrics.get("roc_auc", 0))
    if r2 < 0.5:
        risk_factors.append({"factor": "model_confidence", "score": 60, "explanation": "Low model accuracy"})
    elif r2 < 0.7:
        risk_factors.append({"factor": "model_confidence", "score": 35, "explanation": "Moderate model accuracy"})
    else:
        risk_factors.append({"factor": "model_confidence", "score": 15, "explanation": "High model accuracy"})

    # Uncertainty risk
    if predictions:
        avg_width = np.mean([
            p.get("upper_bound", p["value"]) - p.get("lower_bound", p["value"])
            for p in predictions
        ])
        avg_val = np.mean([p["value"] for p in predictions])
        if avg_val != 0 and avg_width / abs(avg_val) > 0.5:
            risk_factors.append({"factor": "uncertainty", "score": 50, "explanation": "Wide confidence intervals"})
        else:
            risk_factors.append({"factor": "uncertainty", "score": 15, "explanation": "Narrow confidence intervals"})

    overall = int(np.mean([r["score"] for r in risk_factors]))

    return {
        "risk_score": overall,
        "risk_factors": risk_factors,
        "overall_assessment": "high" if overall > 60 else "medium" if overall > 30 else "low",
    }
