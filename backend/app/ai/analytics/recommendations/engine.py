"""Generate business recommendations from insights, anomalies, and root causes.

Uses rule-based generation combined with LLM enhancement when available.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.ai.analytics.schemas import (
    Anomaly,
    Confidence,
    Insight,
    Recommendation,
    RootCause,
)


def _rid() -> str:
    return uuid.uuid4().hex[:12]


def generate_recommendations(
    insights: list[Insight],
    anomalies: list[Anomaly],
    root_causes: list[RootCause],
    data_context: dict[str, Any] | None = None,
) -> list[Recommendation]:
    """Generate actionable business recommendations from analysis results.

    Combines rule-based templates with data-driven evidence.
    """
    recs: list[Recommendation] = []

    # --- Rule-based from negative trends ---
    neg_insights = [i for i in insights if i.type.value == "negative_trend"]
    for ni in neg_insights:
        recs.append(
            Recommendation(
                id=_rid(),
                title=f"Address declining {ni.metric}",
                description=(
                    f"{ni.metric} has decreased by {abs(ni.change_pct):.1f}%. "
                    f"Investigate root causes and implement corrective actions."
                ),
                category="operations",
                priority="high" if abs(ni.change_pct) > 20 else "medium",
                expected_impact=f"Stabilise {ni.metric} and prevent further decline",
                evidence=ni.evidence,
                confidence=ni.confidence,
                business_logic=(
                    "Declining metrics require immediate attention to prevent "
                    "compounding negative effects."
                ),
                action_items=[
                    f"Review factors contributing to {ni.metric} decline",
                    "Conduct root cause analysis with team leads",
                    "Implement corrective measures within 2 weeks",
                    "Set up monitoring alerts for early warning",
                ],
            )
        )

    # --- Rule-based from positive trends ---
    pos_insights = [i for i in insights if i.type.value == "positive_trend"]
    for pi in pos_insights:
        recs.append(
            Recommendation(
                id=_rid(),
                title=f"Scale successful {pi.metric} initiatives",
                description=(
                    f"{pi.metric} is growing at {pi.change_pct:.1f}%. "
                    f"Identify and replicate the driving factors."
                ),
                category="growth",
                priority="medium",
                expected_impact=f"Accelerate {pi.metric} growth by scaling what works",
                evidence=pi.evidence,
                confidence=pi.confidence,
                business_logic="Positive momentum should be amplified, not assumed to continue.",
                action_items=[
                    f"Document what is driving {pi.metric} growth",
                    "Allocate additional resources to high-performing channels",
                    "Set stretch targets to maintain momentum",
                ],
            )
        )

    # --- Rule-based from top/bottom products ---
    top_products = [i for i in insights if i.type.value == "top_product"]
    for tp in top_products:
        recs.append(
            Recommendation(
                id=_rid(),
                title=f"Increase inventory for {tp.metric}",
                description=(
                    f"{tp.metric} is the top performer with {tp.current_value:.0f}. "
                    f"Ensure supply meets demand."
                ),
                category="operations",
                priority="medium",
                expected_impact="Prevent stockouts and maximise revenue from top performer",
                evidence=tp.evidence,
                confidence=tp.confidence,
                business_logic="Stockouts on top products directly lose revenue.",
                action_items=[
                    f"Increase {tp.metric} inventory by 20-30%",
                    "Review supplier lead times",
                    "Set up automated reorder alerts",
                ],
            )
        )

    worst_products = [i for i in insights if i.type.value == "worst_product"]
    for wp in worst_products:
        recs.append(
            Recommendation(
                id=_rid(),
                title=f"Review underperforming {wp.metric}",
                description=(
                    f"{wp.metric} is the worst performer at {wp.current_value:.0f}. "
                    f"Evaluate whether to improve or discontinue."
                ),
                category="product",
                priority="medium",
                expected_impact=f"Free up resources from {wp.metric} or improve its performance",
                evidence=wp.evidence,
                confidence=wp.confidence,
                business_logic="Underperforming products consume resources without proportional return.",
                action_items=[
                    f"Analyse root causes for {wp.metric} underperformance",
                    "Consider promotional campaigns or product improvements",
                    "Evaluate discontinuation if ROI is negative",
                ],
            )
        )

    # --- Rule-based from anomalies ---
    high_sev_anomalies = [a for a in anomalies if a.severity == "high"]
    for anom in high_sev_anomalies:
        recs.append(
            Recommendation(
                id=_rid(),
                title=f"Investigate anomaly in {anom.metric}",
                description=(
                    f"Unusual {anom.type.value} detected in {anom.metric}. "
                    f"Severity: {anom.severity}. Immediate investigation recommended."
                ),
                category="operations",
                priority="critical",
                expected_impact="Prevent potential business disruption from unaddressed anomalies",
                evidence=anom.evidence,
                confidence=anom.confidence,
                business_logic="High-severity anomalies may indicate systemic issues.",
                action_items=[
                    f"Review {anom.metric} data for the affected period",
                    "Check for data pipeline issues",
                    "Escalate to relevant team leads",
                ],
            )
        )

    # --- Rule-based from root causes ---
    for rc in root_causes:
        if rc.contribution_pct > 20:
            recs.append(
                Recommendation(
                    id=_rid(),
                    title=f"Address root cause: {rc.factor}",
                    description=(
                        f"'{rc.factor}' contributes {rc.contribution_pct:.0f}% to the observed change. "
                        f"{rc.explanation}"
                    ),
                    category="operations",
                    priority="high" if rc.contribution_pct > 40 else "medium",
                    expected_impact=f"Resolve {rc.contribution_pct:.0f}% of the issue by addressing this factor",
                    evidence=rc.evidence,
                    confidence=Confidence.HIGH,
                    business_logic="Addressing high-contribution root causes yields the highest ROI.",
                    action_items=[
                        f"Develop action plan for '{rc.factor}'",
                        "Assign responsible team member",
                        "Set deadline for corrective measures",
                    ],
                )
            )

    # --- Seasonality-based ---
    season_insights = [i for i in insights if i.type.value == "seasonality"]
    for si in season_insights:
        recs.append(
            Recommendation(
                id=_rid(),
                title=f"Prepare for seasonal pattern in {si.metric}",
                description=(
                    f"Seasonal patterns detected in {si.metric}. "
                    f"Adjust operations and marketing accordingly."
                ),
                category="marketing",
                priority="medium",
                expected_impact=f"Optimise {si.metric} by aligning with seasonal demand",
                evidence=si.evidence,
                confidence=si.confidence,
                business_logic="Seasonal anticipation enables proactive resource allocation.",
                action_items=[
                    f"Review historical seasonal patterns for {si.metric}",
                    "Adjust marketing campaigns to align with peak periods",
                    "Scale inventory and staffing for predicted demand",
                ],
            )
        )

    # --- Regional comparison-based ---
    regional = [i for i in insights if i.type.value == "regional_comparison"]
    for ri in regional:
        recs.append(
            Recommendation(
                id=_rid(),
                title="Launch targeted campaign in underperforming regions",
                description=(
                    f"Regional disparities detected: {ri.description}. "
                    f"Targeted campaigns can close the gap."
                ),
                category="marketing",
                priority="medium",
                expected_impact="Reduce regional performance gaps and unlock growth",
                evidence=ri.evidence,
                confidence=ri.confidence,
                business_logic="Regional underperformance often stems from lack of targeted effort.",
                action_items=[
                    "Identify top 3 underperforming regions",
                    "Design region-specific marketing campaigns",
                    "Allocate budget for regional initiatives",
                    "Set KPI targets for regional improvement",
                ],
            )
        )

    # Deduplicate by title
    seen_titles: set[str] = set()
    unique_recs: list[Recommendation] = []
    for rec in recs:
        if rec.title not in seen_titles:
            seen_titles.add(rec.title)
            unique_recs.append(rec)

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    unique_recs.sort(key=lambda r: priority_order.get(r.priority, 99))

    return unique_recs
