"""Tests for the Reporting Engine (stdlib-only paths)."""

from app.reports.distributions.distribution import DistributionEngine
from app.reports.events.events import EventBus
from app.reports.exporters.exporters import SUPPORTED_FORMATS, export_report
from app.reports.generators.builder import ReportBuilder
from app.reports.permissions.permissions import PermissionChecker
from app.reports.renderers.html_renderer import render_html
from app.reports.repositories.report_repo import ReportRepository
from app.reports.schedulers.scheduler import Scheduler
from app.reports.services.report_service import ReportService
from app.reports.templates.engine import TemplateEngine


def _definition():
    return {
        "title": "Q1 Sales Report",
        "report_type": "sales",
        "variables": {"region": "EMEA"},
        "sections": [
            {
                "section_id": "kpi",
                "kind": "kpi",
                "title": "Revenue",
                "config": {"kpi": "revenue"},
                "order": 0,
            },
            {
                "section_id": "summary",
                "kind": "summary",
                "title": "Summary",
                "config": {},
                "order": 1,
            },
            {
                "section_id": "notes",
                "kind": "text",
                "title": "Notes",
                "config": {"body": "Reviewed"},
                "order": 2,
            },
        ],
    }


class TestTemplateEngine:
    def test_create_approve_version(self):
        engine = TemplateEngine()
        tpl = engine.create("Corporate", sections=[{"section_id": "a"}])
        assert tpl.current_version == 1
        v2 = engine.update(tpl.template_id, change_note="v2")
        assert v2.version_number == 2
        assert engine.approve(tpl.template_id, 2, "admin") is True
        assert tpl.active_version().version_number == 2

    def test_render_fallback(self):
        engine = TemplateEngine()
        out = engine.render_string("Hello {{ name }}", {"name": "Acme"})
        assert "Acme" in out


class TestBuilder:
    def test_build_all_sections(self):
        import asyncio

        builder = ReportBuilder()
        built = asyncio.run(builder.build(_definition()))
        assert len(built.sections) == 3
        assert built.sections[0].data["source"] == "analytics"

    def test_conditions(self):
        import asyncio

        builder = ReportBuilder()
        definition = _definition()
        definition["sections"].append(
            {
                "section_id": "cond",
                "kind": "text",
                "title": "Hidden",
                "config": {},
                "conditions": {"region": "APAC"},
                "order": 3,
            }
        )
        built = asyncio.run(builder.build(definition, variables={"region": "EMEA"}))
        assert "cond" not in [s.section_id for s in built.sections]


class TestRenderExport:
    def test_html_contains_sections(self):
        html = render_html(
            {
                "title": "T",
                "generated_at": "now",
                "sections": [
                    {"section_id": "a", "kind": "text", "title": "Hi", "data": {"payload": "body"}}
                ],
            },
            {},
        )
        assert "Hi" in html and "body" in html

    def test_stdlib_exports(self, tmp_path):
        report = {
            "title": "T",
            "sections": [
                {"section_id": "a", "kind": "text", "title": "Hi", "data": {"payload": "body"}}
            ],
        }
        for fmt in ["html", "csv", "json", "zip", "svg"]:
            meta = export_report(report, "<html></html>", fmt, tmp_path / f"r.{fmt}")
            assert meta["format"] == fmt
            assert (tmp_path / f"r.{fmt}").exists()

    def test_supported_formats(self):
        assert set(SUPPORTED_FORMATS) >= {
            "pdf",
            "docx",
            "xlsx",
            "csv",
            "json",
            "html",
            "pptx",
            "png",
            "svg",
            "zip",
        }


class TestScheduler:
    def test_daily_next_run(self):
        from datetime import datetime

        sched = Scheduler()
        s = sched.create("r1", frequency="daily")
        assert s.next_run_at is not None and s.next_run_at > datetime(2000, 1, 1)

    def test_pause_resume_retry(self):
        sched = Scheduler()
        s = sched.create("r1", frequency="hourly", max_retries=1)
        assert sched.pause(s.schedule_id) is True
        assert sched.resume(s.schedule_id) is True
        sched.record_run(s.schedule_id, False)
        sched.record_run(s.schedule_id, False)
        assert sched.get(s.schedule_id).enabled is False

    def test_holidays_skipped(self):
        from datetime import datetime

        sched = Scheduler()
        s = sched.create(
            "r1", frequency="daily", holidays=["2030-01-01"], now=datetime(2029, 12, 31, 12, 0)
        )
        assert s.next_run_at.strftime("%Y-%m-%d") != "2030-01-01"


class TestPermissions:
    def test_owner_can_all(self):
        perms = PermissionChecker()
        perms.grant("r1", "u1", role="viewer")
        assert perms.require("r1", "view", "u1", owner_id="owner") == "viewer"
        assert perms.require("r1", "delete", "owner", owner_id="owner") == "owner"
        try:
            perms.require("r1", "delete", "u1", owner_id="owner")
            raise AssertionError("should have raised")
        except PermissionError:
            pass


class TestDistributionEvents:
    def test_shared_link_lifecycle(self):
        engine = DistributionEngine()
        link = engine.create_shared_link("r1")
        assert engine.resolve_link(link.token) is not None
        assert engine.revoke_link(link.token) is True
        assert engine.resolve_link(link.token) is None

    def test_events(self):
        bus = EventBus()
        bus.publish("report_generated", "r1")
        assert len(bus.history("r1")) == 1


class TestService:
    def test_generate_html_json(self, tmp_path):
        import asyncio

        service = ReportService(storage_root=tmp_path)
        record = service.create_report(
            {"title": "Q1", "report_type": "sales", "definition": _definition(), "tags": []},
            owner_id="u1",
            organization_id="o1",
        )
        result = asyncio.run(
            service.generate(
                report_id=record["id"],
                formats=["html", "json", "csv"],
                include_ai=False,
                user_id="u1",
                organization_id="o1",
            )
        )
        assert result["version_number"] == 1
        assert len(result["artifacts"]) == 3
        assert len(service.repo.versions(record["id"])) == 1

    def test_repo_search_compare(self):
        repo = ReportRepository()
        r = repo.create(
            {"title": "Sales Q1", "report_type": "sales", "definition": {"sections": []}}
        )
        assert repo.list(search="sales")
        repo.add_version(r["id"], {"definition_snapshot": {"sections": []}})
        repo.add_version(r["id"], {"definition_snapshot": {"sections": [{"section_id": "a"}]}})
        cmp = repo.compare(r["id"], 1, 2)
        assert cmp["added_sections"] == ["a"]
