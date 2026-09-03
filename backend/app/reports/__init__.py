"""Reporting & Document Automation Engine (Phase 14).

Packages:
- templates: reusable branded templates, versioning, approval
- generators: ReportBuilder assembling analytics/dashboard/AI content
- renderers: HTML canonical renderer (PDF/PNG derive from it)
- exporters: pdf, docx, xlsx, csv, json, html, pptx, png, svg, zip
- schedulers: intervals, cron, timezones, holidays, pause/resume, retries
- distributions: download, email, shared links, org sharing, webhooks
- repositories: persistence-agnostic report/version store
- routers: FastAPI endpoints (/reports)
- services: ReportService orchestrating the full workflow
- schemas: Pydantic contracts
- models: SQLAlchemy records (reports, versions, templates, schedules, deliveries, shares)
- jobs: Celery-compatible background tasks
- cache: TTL report cache
- permissions: RBAC enforcement (owner/editor/reviewer/viewer)
- events: event bus + audit trail
- utils: helpers
- tests/docs: suites and guides
"""

from app.reports.services.report_service import ReportService

__all__ = ["ReportService"]
