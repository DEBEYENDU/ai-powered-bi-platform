"""Generate executive summaries from analysis results.

Uses LLM when available, falls back to structured template-based summaries.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.ai.analytics.prompts.templates import SUMMARY_PROMPTS, SYSTEM_PROMPT
from app.ai.analytics.schemas import (
    Anomaly,
    Insight,
    Recommendation,
    Summary,
    SummaryType,
)


async def _llm_summary(
    analysis_context: str,
    summary_type: str,
    provider: Any,
) -> str | None:
    """Attempt to generate a summary via LLM. Returns None on failure."""
    try:
        prompt_template = SUMMARY_PROMPTS.get(summary_type, SUMMARY_PROMPTS["executive_brief"])
        prompt = prompt_template.format(analysis_context=analysis_context)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        response = await provider.chat(messages)
        return response.get("content", "")
    except Exception:  # noqa: BLE001
        return None


def _build_analysis_context(
    insights: list[Insight],
    anomalies: list[Anomaly],
    recommendations: list[Recommendation],
    forecast_summary: dict[str, Any] | None,
) -> str:
    """Build a text context from analysis results for LLM consumption."""
    lines: list[str] = []

    if insights:
        lines.append("KEY INSIGHTS:")
        for i in insights[:10]:
            lines.append(
                f"- [{i.type.value}] {i.title}: {i.description} "
                f"(confidence: {i.confidence.value}, change: {i.change_pct:.1f}%)"
            )

    if anomalies:
        lines.append("\nANOMALIES DETECTED:")
        for a in anomalies[:10]:
            lines.append(
                f"- [{a.type.value}] {a.title}: {a.description} "
                f"(severity: {a.severity}, metric: {a.metric})"
            )

    if recommendations:
        lines.append("\nRECOMMENDATIONS:")
        for r in recommendations[:7]:
            lines.append(f"- [{r.priority}] {r.title}: {r.description}")

    if forecast_summary:
        lines.append(f"\nFORECAST: {forecast_summary.get('trend', 'N/A')} trend")
        lines.append(
            f"  Seasonality: {'Detected' if forecast_summary.get('seasonality_detected') else 'None'}"
        )

    return "\n".join(lines)


def _template_summary(
    summary_type: SummaryType,
    insights: list[Insight],
    anomalies: list[Anomaly],
    recommendations: list[Recommendation],
) -> str:
    """Generate a structured summary without LLM."""
    sections: list[str] = []

    # Header
    type_labels = {
        SummaryType.BOARD: "Board Meeting Summary",
        SummaryType.CEO: "CEO Executive Summary",
        SummaryType.FINANCE: "Finance Summary",
        SummaryType.SALES: "Sales Summary",
        SummaryType.MARKETING: "Marketing Summary",
        SummaryType.OPERATIONS: "Operations Summary",
        SummaryType.EXECUTIVE_BRIEF: "Executive Brief",
    }
    sections.append(f"# {type_labels.get(summary_type, 'Executive Summary')}")
    sections.append(f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    sections.append("")

    # Key metrics
    pos_insights = [i for i in insights if i.type.value in ("positive_trend", "highest_growth")]
    neg_insights = [i for i in insights if i.type.value in ("negative_trend", "lowest_growth")]

    if pos_insights:
        sections.append("## Positive Trends")
        for i in pos_insights[:5]:
            sections.append(f"- **{i.title}**: {i.description} (+{i.change_pct:.1f}%)")
        sections.append("")

    if neg_insights:
        sections.append("## Areas of Concern")
        for i in neg_insights[:5]:
            sections.append(f"- **{i.title}**: {i.description} ({i.change_pct:.1f}%)")
        sections.append("")

    # Risks
    high_anomalies = [a for a in anomalies if a.severity in ("high", "medium")]
    if high_anomalies:
        sections.append("## Risks")
        for a in high_anomalies[:5]:
            sections.append(f"- **{a.title}**: {a.description} (severity: {a.severity})")
        sections.append("")

    # Recommendations
    if recommendations:
        sections.append("## Recommended Actions")
        for r in recommendations[:5]:
            sections.append(f"- **[{r.priority.upper()}]** {r.title}: {r.description}")
        sections.append("")

    return "\n".join(sections)


async def generate_summary(
    summary_type: SummaryType,
    insights: list[Insight],
    anomalies: list[Anomaly],
    recommendations: list[Recommendation],
    forecast_summary: dict[str, Any] | None = None,
    provider: Any = None,
) -> Summary:
    """Generate an executive summary from analysis results."""
    analysis_context = _build_analysis_context(
        insights, anomalies, recommendations, forecast_summary
    )

    content: str | None = None
    if provider is not None:
        content = await _llm_summary(analysis_context, summary_type.value, provider)

    if content is None:
        content = _template_summary(summary_type, insights, anomalies, recommendations)

    # Extract key metrics
    key_metrics: list[dict[str, Any]] = []
    for i in insights[:5]:
        key_metrics.append(
            {
                "metric": i.metric,
                "value": i.current_value,
                "change_pct": i.change_pct,
                "direction": "up" if i.change_pct > 0 else "down",
            }
        )

    # Extract risks and opportunities
    risks = [f"{a.title}: {a.description}" for a in anomalies if a.severity in ("high", "medium")][
        :5
    ]
    opportunities = [
        f"{i.title}: {i.description}"
        for i in insights
        if i.type.value in ("positive_trend", "highest_growth")
    ][:5]

    return Summary(
        summary_type=summary_type,
        content=content,
        key_metrics=key_metrics,
        risks=risks,
        opportunities=opportunities,
        generated_at=datetime.now(UTC).isoformat(),
    )
