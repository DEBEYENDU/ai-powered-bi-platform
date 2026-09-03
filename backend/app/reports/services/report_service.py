"""Report service — orchestrates builder, templates, exporters, scheduler,
distribution, permissions, events, and audit.

Workflow: request → permission validation → builder (analytics/dashboard/AI)
→ template layout → HTML render → exporters → storage → distribution → audit.
AI sections reuse the AI Assistant and always carry citations through.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.reports.cache.cache import ReportCache
from app.reports.distributions.distribution import DistributionEngine
from app.reports.events.events import EventBus
from app.reports.exporters.exporters import SUPPORTED_FORMATS, export_report
from app.reports.generators.builder import ReportBuilder
from app.reports.permissions.permissions import PermissionChecker
from app.reports.renderers.html_renderer import render_html
from app.reports.repositories.report_repo import ReportRepository
from app.reports.schedulers.scheduler import Scheduler
from app.reports.templates.engine import TemplateEngine


class ReportService:
    def __init__(self, storage_root: Optional[Path] = None,
                 builder: Optional[ReportBuilder] = None) -> None:
        self.storage_root = storage_root or Path("/tmp/reports")
        self.repo = ReportRepository()
        self.templates = TemplateEngine()
        self.builder = builder or ReportBuilder()
        self.scheduler = Scheduler()
        self.distribution = DistributionEngine(storage_root=self.storage_root)
        self.permissions = PermissionChecker()
        self.events = EventBus()
        self.cache = ReportCache()
        self._audit: List[Dict[str, Any]] = []

    # -- reports --
    def create_report(self, data: Dict[str, Any], owner_id: str = "",
                      organization_id: str = "") -> Dict[str, Any]:
        record = self.repo.create({**data, "owner_id": owner_id,
                                   "organization_id": organization_id})
        self.permissions.grant(record["id"], owner_id or "owner", role="owner",
                               can_export=True, can_distribute=True)
        self._log("report_created", record["id"], owner_id, organization_id, {})
        self.events.publish("report_generated", record["id"], owner_id, organization_id,
                            {"action": "created"})
        return record

    async def generate(self, report_id: Optional[str] = None,
                       definition: Optional[Dict[str, Any]] = None,
                       formats: Optional[List[str]] = None, include_ai: bool = True,
                       ai_sections: Optional[List[str]] = None,
                       variables: Optional[Dict[str, Any]] = None,
                       user_id: str = "", organization_id: str = "") -> Dict[str, Any]:
        start = time.time()
        formats = formats or ["html"]
        for fmt in formats:
            if fmt.lower() not in SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported format '{fmt}'")

        if report_id:
            record = self.repo.get(report_id)
            if record is None:
                raise ValueError(f"Report '{report_id}' not found")
            self.permissions.require(report_id, "export", user_id or record.get("owner_id", ""),
                                     owner_id=record.get("owner_id"))
            definition = record.get("definition", {})
        if not definition:
            raise ValueError("No report definition provided")

        cache_key = self.cache.key("generate", definition=definition,
                                   formats=formats, variables=variables or {})
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        built = await self.builder.build(definition, variables, include_ai, ai_sections)
        layout: Dict[str, Any] = {}
        template_id = (definition.get("template_id") or "")
        if template_id:
            try:
                layout = self.templates.apply_layout(template_id, {"title": built.title, **(variables or {})})
            except ValueError:
                layout = {}
        report_dict = built.dict() if hasattr(built, "dict") else dict(built)
        html = render_html(report_dict, layout)

        artifacts: List[Dict[str, Any]] = []
        storage_paths: Dict[str, str] = {}
        out_dir = self.storage_root / (report_id or built.report_id)
        for fmt in formats:
            out_path = out_dir / f"report.{fmt.lower()}"
            meta = export_report(report_dict, html, fmt, out_path)
            checksum = self._checksum(out_path)
            artifacts.append({"format": fmt.lower(), "storage_path": str(out_path),
                              "file_size": out_path.stat().st_size if out_path.exists() else 0,
                              "checksum_sha256": checksum, **meta})
            storage_paths[fmt.lower()] = str(out_path)

        citations = [c for s in built.sections for c in (s.citations or [])]
        version_number = 1
        if report_id:
            version = self.repo.add_version(report_id, {
                "definition_snapshot": definition,
                "rendered_formats": formats,
                "storage_paths": storage_paths,
                "checksum_sha256": artifacts[0]["checksum_sha256"] if artifacts else "",
            })
            version_number = version["version_number"]

        elapsed_ms = round((time.time() - start) * 1000, 2)
        result = {"report_id": report_id or built.report_id, "version_number": version_number,
                  "artifacts": artifacts, "execution_time_ms": elapsed_ms,
                  "ai_citations": citations, "warnings": built.warnings}
        self.cache.set(cache_key, result, ttl=300.0)
        self._log("report_generated", result["report_id"], user_id, organization_id,
                  {"formats": formats, "execution_time_ms": elapsed_ms})
        self.events.publish("report_generated", result["report_id"], user_id, organization_id,
                            {"formats": formats, "version": version_number})
        return result

    def preview(self, definition: Dict[str, Any], variables: Optional[Dict[str, Any]] = None) -> str:
        stub = {"title": definition.get("title", "Preview"),
                "generated_at": "preview",
                "sections": [{"section_id": s.get("section_id", ""), "kind": s.get("kind", "text"),
                              "title": s.get("title", ""),
                              "data": {"source": "preview", "payload": s.get("config", {})}}
                             for s in definition.get("sections", [])]}
        return render_html(stub, {})

    # -- audit --
    def audit_trail(self, report_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if report_id is None:
            return list(self._audit)
        return [e for e in self._audit if e.get("report_id") == report_id]

    def _log(self, action: str, report_id: str, user_id: str,
             organization_id: str, details: Dict[str, Any]) -> None:
        import datetime as _dt
        self._audit.append({"action": action, "report_id": report_id, "user_id": user_id,
                            "organization_id": organization_id, "details": details,
                            "timestamp": _dt.datetime.utcnow().isoformat()})

    @staticmethod
    def _checksum(path: Path) -> str:
        h = hashlib.sha256()
        try:
            with path.open("rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        except OSError:
            return ""
