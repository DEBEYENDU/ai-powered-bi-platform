"""Report builder.

Assembles a report document model from a definition by pulling data from
existing services — analytics KPIs, dashboard summaries, AI insights — without
duplicating their logic. All service calls are optional/lazy so the builder
works in tests and in deployments where those modules are unavailable.
"""

from __future__ import annotations

import contextlib
import time
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class BuiltSectionModel(BaseModel):
    section_id: str
    kind: str
    title: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    render_order: int = 0


class BuiltReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    report_type: str = "custom"
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    variables: dict[str, Any] = Field(default_factory=dict)
    sections: list[BuiltSectionModel] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class ReportBuilder:
    """Builds report content from definitions + existing platform services."""

    def __init__(
        self,
        analytics_fetcher: Any | None = None,
        dashboard_fetcher: Any | None = None,
        ai_assistant: Any | None = None,
    ) -> None:
        # Callables injected by the service layer; defaults use lazy imports.
        self.analytics_fetcher = analytics_fetcher or self._default_analytics
        self.dashboard_fetcher = dashboard_fetcher or self._default_dashboard
        self.ai_assistant = ai_assistant or self._default_ai

    async def build(
        self,
        definition: dict[str, Any],
        variables: dict[str, Any] | None = None,
        include_ai: bool = True,
        ai_sections: list[str] | None = None,
    ) -> BuiltReport:
        start = time.time()
        variables = variables or {}
        ai_sections = ai_sections or ["summary", "insights", "recommendations"]
        sections = definition.get("sections", [])
        built: list[BuiltSectionModel] = []
        warnings: list[str] = []

        for idx, section in enumerate(sorted(sections, key=lambda s: s.get("order", 0))):
            if not self._conditions_met(section.get("conditions", {}), variables):
                continue
            kind = section.get("kind", "text")
            try:
                data, citations = await self._build_section(
                    kind, section, variables, include_ai, ai_sections
                )
            except Exception as exc:  # never fail the whole report on one section
                warnings.append(f"Section {section.get('section_id')} failed: {exc}")
                data, citations = {"error": str(exc)}, []
            built.append(
                BuiltSectionModel(
                    section_id=section.get("section_id", f"section_{idx}"),
                    kind=kind,
                    title=section.get("title"),
                    data=data,
                    citations=citations,
                    render_order=idx,
                )
            )

        return BuiltReport(
            title=definition.get("title", "Untitled Report"),
            report_type=definition.get("report_type", "custom"),
            variables=variables,
            sections=built,
            execution_time_ms=round((time.time() - start) * 1000, 2),
            warnings=warnings,
        )

    async def _build_section(
        self,
        kind: str,
        section: dict[str, Any],
        variables: dict[str, Any],
        include_ai: bool,
        ai_sections: list[str],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        config = dict(section.get("config", {}))
        config.update({k: v for k, v in variables.items() if k not in config})

        if kind in ("kpi", "chart", "table", "pivot", "heatmap", "trend"):
            data = await self._call(self.analytics_fetcher, config)
            return {"source": "analytics", "payload": data}, []
        if kind in ("dashboard",):
            data = await self._call(self.dashboard_fetcher, config)
            return {"source": "dashboard", "payload": data}, []
        if kind in ("summary", "insights", "recommendations", "root_cause", "forecast_text"):
            if not include_ai or (kind not in ai_sections and kind != "summary"):
                return {"source": "ai", "skipped": True}, []
            result = await self._call(self.ai_assistant, {"section": kind, "config": config})
            payload = result if isinstance(result, dict) else {"text": str(result)}
            citations = payload.get("citations", []) if isinstance(payload, dict) else []
            return {"source": "ai", "payload": payload}, citations
        # text, image, toc, signature, qr, appendix, list: static content
        return {"source": "static", "payload": config}, []

    def _conditions_met(self, conditions: dict[str, Any], variables: dict[str, Any]) -> bool:
        return all(variables.get(key) == expected for key, expected in conditions.items())

    async def _call(self, fn: Any, payload: dict[str, Any]) -> Any:
        import asyncio

        result = fn(payload)
        if asyncio.iscoroutine(result):
            return await result
        return result

    # -- default fetchers (lazy, reuse existing modules when present) --
    def _default_analytics(self, config: dict[str, Any]) -> dict[str, Any]:
        with contextlib.suppress(Exception):
            from app.analytics.kpi.definitions import KPI_DEFINITIONS  # type: ignore

            kpi = str(config.get("kpi", "")).lower()
            if kpi and kpi in KPI_DEFINITIONS:
                definition = KPI_DEFINITIONS[kpi]
                return {"kpi": kpi, "description": str(definition)}
        return {"echo": config}

    def _default_dashboard(self, config: dict[str, Any]) -> dict[str, Any]:
        return {"echo": config}

    def _default_ai(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "text": f"AI section '{payload.get('section')}' (assistant unavailable)",
            "citations": [],
        }
