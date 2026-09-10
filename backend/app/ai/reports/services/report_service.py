"""Main report generation service — orchestrates the full pipeline."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.ai.reports.exporters.engine import export_report
from app.ai.reports.services.ai_service import AIService
from app.ai.reports.services.data_service import DataService
from app.ai.reports.summaries.generator import generate_executive_summary
from app.ai.reports.templates.registry import get_template
from app.ai.reports.validators.validator import validate_all


def _uid() -> str:
    return uuid.uuid4().hex[:12]


class ReportGeneratorService:
    """Orchestrates AI report generation: data load → AI → export → persist."""

    def __init__(self, engine: Engine, db: Session) -> None:
        self._engine = engine
        self._db = db
        self._data_service = DataService(engine)

    def _get_ai_service(self) -> AIService:
        try:
            from app.ai.providers.registry import get_provider
            return AIService(provider=get_provider())
        except Exception:  # noqa: BLE001
            return AIService(provider=None)

    def _get_storage_dir(self) -> str:
        import os
        from pathlib import Path
        base = os.getenv("REPORTS_PATH", str(Path(__file__).resolve().parents[4] / "reports"))
        path = Path(base)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def _save_report(self, report_id: str, data: dict[str, Any]) -> None:
        """Persist report to database."""
        try:
            self._db.execute(
                text("""
                    INSERT INTO ai_reports (id, organization_id, owner_id, title, description,
                        prompt, report_type, status, dashboard_id, executive_summary,
                        sections, kpis, charts, insights, risks, recommendations,
                        branding, tags, current_version, generation_time_ms, created_at, updated_at)
                    VALUES (:id, :org_id, :owner_id, :title, :desc,
                        :prompt, :type, :status, :dash_id, :summary,
                        :sections, :kpis, :charts, :insights, :risks, :recs,
                        :branding, :tags, :version, :time_ms, :now, :now)
                """),
                {
                    "id": report_id,
                    "org_id": data.get("organization_id", "00000000-0000-0000-0000-000000000000"),
                    "owner_id": data.get("owner_id", "00000000-0000-0000-0000-000000000000"),
                    "title": data.get("title", ""),
                    "desc": data.get("description", ""),
                    "prompt": data.get("prompt", ""),
                    "type": data.get("report_type", "custom"),
                    "status": data.get("status", "completed"),
                    "dash_id": data.get("dashboard_id"),
                    "summary": data.get("executive_summary", ""),
                    "sections": data.get("sections", []),
                    "kpis": data.get("kpis", []),
                    "charts": data.get("charts", []),
                    "insights": data.get("insights", []),
                    "risks": data.get("risks", []),
                    "recs": data.get("recommendations", []),
                    "branding": data.get("branding", {}),
                    "tags": data.get("tags", []),
                    "version": 1,
                    "time_ms": data.get("generation_time_ms", 0),
                    "now": datetime.now(UTC),
                },
            )
            self._db.commit()
        except Exception:  # noqa: BLE001
            self._db.rollback()

    def _save_version(self, report_id: str, version: int, data: dict[str, Any], formats: list[str]) -> None:
        """Persist a version snapshot."""
        try:
            self._db.execute(
                text("""
                    INSERT INTO ai_report_versions (id, report_id, version_number,
                        content_snapshot, formats_generated, storage_paths, created_at)
                    VALUES (:id, :report_id, :version, :snapshot, :formats, :paths, :now)
                """),
                {
                    "id": _uid(),
                    "report_id": report_id,
                    "version": version,
                    "snapshot": {
                        "title": data.get("title", ""),
                        "sections": data.get("sections", []),
                        "executive_summary": data.get("executive_summary", ""),
                    },
                    "formats": formats,
                    "paths": {},
                    "now": datetime.now(UTC),
                },
            )
            self._db.commit()
        except Exception:  # noqa: BLE001
            self._db.rollback()

    async def generate(
        self,
        prompt: str,
        dashboard_id: str | None = None,
        report_type: str = "custom",
        formats: list[str] | None = None,
        branding: dict[str, Any] | None = None,
        organization_id: str | None = None,
    ) -> dict[str, Any]:
        """Full report generation pipeline."""
        start = time.monotonic()
        formats = formats or ["pdf"]
        branding = branding or {}
        report_id = _uid()

        # Validate
        err = validate_all(prompt, report_type, formats, branding)
        if err:
            return {"success": False, "error": err}

        # Load data
        dashboard: dict[str, Any] | None = None
        data_context = ""
        kpis_from_data: list[dict[str, Any]] = []
        chart_data: list[dict[str, Any]] = []

        if dashboard_id:
            try:
                dashboard = self._data_service.load_dashboard_data(dashboard_id)
                data_context = self._data_service.build_data_context(dashboard)
                kpis_from_data = self._data_service.extract_kpis(dashboard)
                chart_data = self._data_service.extract_chart_data(dashboard)
            except Exception as e:  # noqa: BLE001
                data_context = f"Dashboard {dashboard_id} could not be loaded: {e}"

        # Generate content via AI
        ai = self._get_ai_service()
        kpis_ctx = "\n".join(
            f"- {k['name']}: {k['value']} {k.get('unit', '')}" for k in kpis_from_data[:20]
        )
        chart_ctx = "\n".join(
            f"- {c['title']} ({c['chart_type']}): {len(c.get('data', []))} data points"
            for c in chart_data[:10]
        )

        ai_content = await ai.generate_report_content(
            prompt=prompt,
            report_type=report_type,
            data_context=data_context,
            kpis_context=kpis_ctx,
            chart_context=chart_ctx,
        )

        # Generate executive summary
        summary_data = {
            "report_type": report_type,
            "kpis": kpis_from_data,
            "charts": chart_data,
            "prompt": prompt,
        }
        exec_summary = await generate_executive_summary(
            report_type=report_type,
            data=summary_data,
            provider=self._get_ai_service()._provider,
        )

        # Build final report
        report_data: dict[str, Any] = {
            "title": ai_content.get("title", f"{report_type.title()} Report"),
            "description": f"Generated from: {prompt[:200]}",
            "report_type": report_type,
            "executive_summary": exec_summary or ai_content.get("executive_summary", ""),
            "sections": ai_content.get("sections", []),
            "kpis": ai_content.get("kpis", []) or kpis_from_data,
            "charts": ai_content.get("charts", []) or chart_data,
            "insights": ai_content.get("insights", []),
            "risks": ai_content.get("risks", []),
            "recommendations": ai_content.get("recommendations", []),
            "prompt": prompt,
            "dashboard_id": dashboard_id,
            "organization_id": organization_id or "00000000-0000-0000-0000-000000000000",
        }

        # Export to requested formats
        storage_dir = self._get_storage_dir()
        download_urls: list[dict[str, Any]] = []
        for fmt in formats:
            file_path = f"{storage_dir}/{report_id}/{report_id}.{fmt}"
            try:
                result = export_report(report_data, fmt, __import__("pathlib").Path(file_path))
                download_urls.append({
                    "format": fmt,
                    "url": f"/api/v1/ai/reports/{report_id}/download?format={fmt}",
                    "file_size": result.get("file_size", 0),
                })
            except Exception as e:  # noqa: BLE001
                download_urls.append({"format": fmt, "url": "", "error": str(e)})

        elapsed = (time.monotonic() - start) * 1000
        report_data["generation_time_ms"] = round(elapsed, 2)
        report_data["status"] = "completed"

        # Persist
        self._save_report(report_id, {**report_data, "owner_id": "00000000-0000-0000-0000-000000000000"})
        self._save_version(report_id, 1, report_data, formats)

        get_template(report_type)
        return {
            "success": True,
            "report_id": report_id,
            "title": report_data["title"],
            "status": "completed",
            "report_type": report_type,
            "sections": report_data["sections"],
            "kpis": report_data["kpis"],
            "charts": report_data["charts"],
            "insights": report_data["insights"],
            "risks": report_data["risks"],
            "recommendations": report_data["recommendations"],
            "executive_summary": report_data["executive_summary"],
            "download_urls": download_urls,
            "versions": [{"version": 1, "created_at": datetime.now(UTC).isoformat()}],
            "generation_time_ms": round(elapsed, 2),
        }

    async def followup(self, report_id: str, question: str) -> dict[str, Any]:
        """Answer a follow-up question about a report."""
        try:
            result = self._db.execute(
                text("SELECT title, executive_summary, sections, insights, recommendations FROM ai_reports WHERE id = :id"),
                {"id": report_id},
            )
            row = result.fetchone()
            if row is None:
                return {"answer": f"Report {report_id} not found.", "confidence": "low"}

            report_context = f"Title: {row[0]}\nSummary: {row[1]}\nSections: {row[2]}\nInsights: {row[3]}\nRecommendations: {row[4]}"
            ai = self._get_ai_service()
            answer = await ai.followup(report_context, question)
            return {"answer": answer, "confidence": "medium", "evidence": []}
        except Exception as e:  # noqa: BLE001
            return {"answer": f"Error: {e}", "confidence": "low", "evidence": []}

    def list_reports(
        self, page: int = 1, page_size: int = 20, search: str = "", report_type: str | None = None
    ) -> dict[str, Any]:
        """List AI reports with pagination and filters."""
        try:
            where_parts: list[str] = ["deleted_at IS NULL"]
            params: dict[str, Any] = {}

            if search:
                where_parts.append("(title ILIKE :search OR prompt ILIKE :search)")
                params["search"] = f"%{search}%"
            if report_type:
                where_parts.append("report_type = :type")
                params["type"] = report_type

            where = " AND ".join(where_parts)
            offset = (page - 1) * page_size
            params["limit"] = page_size
            params["offset"] = offset

            count_result = self._db.execute(
                text("SELECT COUNT(*) FROM ai_reports WHERE " + where), params
            )
            total = count_result.scalar() or 0

            result = self._db.execute(
                text(
                    "SELECT id, title, report_type, status, executive_summary,"
                    " generation_time_ms, created_at, tags"
                    " FROM ai_reports WHERE " + where +
                    " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                ),
                params,
            )
            reports = []
            for row in result.fetchall():
                reports.append({
                    "id": str(row[0]),
                    "title": row[1],
                    "report_type": row[2],
                    "status": row[3],
                    "executive_summary": (row[4] or "")[:200],
                    "generation_time_ms": row[5],
                    "created_at": str(row[6]) if row[6] else "",
                    "tags": row[7] or [],
                })

            return {"reports": reports, "total": total, "page": page, "page_size": page_size}
        except Exception:  # noqa: BLE001
            return {"reports": [], "total": 0, "page": page, "page_size": page_size}

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        """Get a single AI report by ID."""
        try:
            result = self._db.execute(
                text("""
                    SELECT id, title, description, report_type, status, prompt,
                        dashboard_id, executive_summary, sections, kpis, charts,
                        insights, risks, recommendations, tags,
                        generation_time_ms, created_at
                    FROM ai_reports WHERE id = :id AND deleted_at IS NULL
                """),
                {"id": report_id},
            )
            row = result.fetchone()
            if row is None:
                return None

            return {
                "id": str(row[0]),
                "title": row[1],
                "description": row[2],
                "report_type": row[3],
                "status": row[4],
                "prompt": row[5],
                "dashboard_id": row[6],
                "executive_summary": row[7],
                "sections": row[8] or [],
                "kpis": row[9] or [],
                "charts": row[10] or [],
                "insights": row[11] or [],
                "risks": row[12] or [],
                "recommendations": row[13] or [],
                "tags": row[14] or [],
                "generation_time_ms": row[15],
                "created_at": str(row[16]) if row[16] else "",
                "download_urls": [],
                "versions": [],
            }
        except Exception:  # noqa: BLE001
            return None

    def delete_report(self, report_id: str) -> bool:
        """Soft-delete an AI report."""
        try:
            self._db.execute(
                text("UPDATE ai_reports SET deleted_at = :now WHERE id = :id"),
                {"id": report_id, "now": datetime.now(UTC)},
            )
            self._db.commit()
            return True
        except Exception:  # noqa: BLE001
            self._db.rollback()
            return False
