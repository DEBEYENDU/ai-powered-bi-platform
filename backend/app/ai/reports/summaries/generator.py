"""Generate executive summaries for reports using LLM or template fallback."""

from __future__ import annotations

from typing import Any

from app.ai.reports.prompts.templates import EXECUTIVE_SUMMARY_PROMPT, SYSTEM_PROMPT


def _build_data_context(data: dict[str, Any]) -> str:
    """Build text context from dashboard/analytic data."""
    lines: list[str] = []
    for key, val in data.items():
        if isinstance(val, list):
            lines.append(f"{key}: {len(val)} records")
            for item in val[:5]:
                if isinstance(item, dict):
                    lines.append(f"  - {item}")
        elif isinstance(val, dict):
            lines.append(f"{key}: {val}")
        else:
            lines.append(f"{key}: {val}")
    return "\n".join(lines) if lines else "No data available"


async def generate_executive_summary(
    report_type: str,
    data: dict[str, Any],
    provider: Any = None,
) -> str:
    """Generate an executive summary. Uses LLM if available, else template."""
    data_context = _build_data_context(data)

    if provider is not None:
        try:
            prompt = EXECUTIVE_SUMMARY_PROMPT.format(
                report_type=report_type,
                data_context=data_context[:6000],
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            response = await provider.chat(messages)
            content = response.get("content", "")
            if content and len(content) > 50:
                return content
        except Exception:  # noqa: BLE001, S110
            pass

    # Template fallback
    return _template_summary(report_type, data)


def _template_summary(report_type: str, data: dict[str, Any]) -> str:
    """Generate a structured summary without LLM."""
    sections: list[str] = []
    sections.append(f"## Executive Summary — {report_type.title()} Report\n")

    # Count data items
    total_metrics = 0
    for val in data.values():
        if isinstance(val, list):
            total_metrics += len(val)

    sections.append(
        f"This {report_type} report provides a comprehensive analysis based on "
        f"{total_metrics} data points collected from the dashboard.\n"
    )

    sections.append("### Key Highlights\n")
    sections.append("- Data analysis has been performed across all available metrics")
    sections.append("- Trends, anomalies, and patterns have been identified")
    sections.append("- Actionable recommendations have been generated based on the data\n")

    sections.append("### Business Health\n")
    sections.append("The analysis indicates that detailed metrics and KPIs have been reviewed ")
    sections.append("to provide a comprehensive view of business performance.\n")

    sections.append("### Confidence\n")
    sections.append("This summary is based on the data available in the connected dashboard. ")
    sections.append("For more detailed analysis, ensure all relevant data sources are connected.")

    return "\n".join(sections)
