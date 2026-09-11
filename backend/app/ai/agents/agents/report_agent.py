"""Report Agent — generates reports, executive summaries, exports."""

from __future__ import annotations

from typing import Any

from app.ai.agents.agents.base import BaseAgent
from app.ai.agents.prompts.templates import REPORT_AGENT_PROMPT


class ReportAgent(BaseAgent):
    agent_type = "report"
    name = "Report Agent"
    description = "Generate reports, executive summaries, export to PDF/PowerPoint/Excel"

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
        tools: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data_summary = context.get("data_summary", "No data")
        analysis = context.get("analysis", "No analysis")
        fmt = context.get("format", "pdf")

        prompt = REPORT_AGENT_PROMPT.format(
            task=task,
            data_summary=data_summary,
            analysis=analysis,
            format=fmt,
        )

        llm_response = await self._call_llm(prompt)

        report_config = self._generate_report_config(context)

        return self._build_result(
            output=llm_response,
            data={
                "report_config": report_config,
                "executive_summary": self._generate_executive_summary(context),
                "sections": self._define_sections(context),
                "export_format": fmt,
            },
            artifacts=[{"type": "report_config", "content": report_config}],
        )

    def _generate_report_config(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": context.get("title", "Business Report"),
            "format": context.get("format", "pdf"),
            "sections": [
                {"title": "Executive Summary", "type": "text"},
                {"title": "Key Metrics", "type": "kpi_grid"},
                {"title": "Trend Analysis", "type": "chart"},
                {"title": "Recommendations", "type": "list"},
            ],
            "branding": {"logo": True, "colors": "default"},
        }

    def _generate_executive_summary(self, context: dict[str, Any]) -> str:
        return "Executive summary will be generated based on the analysis results."

    def _define_sections(self, context: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {"title": "Executive Summary", "description": "High-level overview of findings"},
            {"title": "Data Analysis", "description": "Detailed analysis results"},
            {"title": "Visualizations", "description": "Charts and graphs"},
            {"title": "Recommendations", "description": "Actionable business recommendations"},
            {"title": "Appendix", "description": "Supporting data and methodology"},
        ]
