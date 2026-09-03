# Phase 14 – Reporting, Document Generation & Report Automation Engine

## Overview

Enterprise reporting platform (SSRS / BI Publisher class) built on top of all
previous modules. Reuses Analytics, Dashboard, AI Assistant, and Storage services
without duplicating their logic. AI-generated sections are grounded in analytics
outputs and carry citations end-to-end.

## Workflow

```
User Request → Auth → Permission Validation → Analytics/Dashboard/AI
→ Report Builder → Template Engine → HTML Renderer → Exporters → Storage
→ Distribution → Audit Logging
```

## Module Structure (`backend/app/reports/`)

| Package | Responsibility |
|---|---|
| `templates/` | Branded layouts, versioning, approval, Jinja2 with fallback renderer |
| `generators/` | `ReportBuilder` – assembles KPI/chart/table/AI sections, conditional display, per-section fault isolation |
| `renderers/` | Canonical self-contained HTML (inline CSS); PDF/PNG derive from it |
| `exporters/` | pdf, docx, xlsx, csv, json, html, pptx, png, svg, zip. Stdlib formats always work; office/PDF degrade gracefully without optional deps |
| `schedulers/` | one_time/hourly/daily/weekly/monthly/quarterly/yearly/cron, timezones, holidays, pause/resume, retry backoff, auto-pause |
| `distributions/` | download (signed URLs), email (swappable sender), shared links (TTL+revoke), org sharing, webhook hook; delivery tracking |
| `repositories/` | Persistence-agnostic store, immutable versions, compare/restore |
| `routers/` | 20 FastAPI endpoints under `/reports` |
| `services/` | `ReportService` – full workflow orchestration + audit |
| `schemas/` | Pydantic contracts (definitions, templates, schedules, shares, search) |
| `models/` | SQLAlchemy records: reports, versions, templates, schedules, deliveries, shares |
| `jobs/` | Celery-compatible tasks with sync fallback (no broker needed for tests) |
| `cache/` | TTL report cache |
| `permissions/` | RBAC: owner/editor/reviewer/viewer + export/distribute flags |
| `events/` | Event bus: generated/scheduled/delivered/failed/template/approval/archived |
| `utils/` | slugify, definition summary, pagination |
| `tests/` | 15 tests, all passing |
| `docs/` | `architecture.md` |

## Report Types

executive, sales, financial, inventory, customer, marketing, operations, forecast,
performance, audit, compliance, custom.

## Builder Components

charts, KPI cards, tables, pivot tables, heatmaps, forecast charts, trend analysis,
executive summary, AI insights, recommendations, images, rich text, lists,
appendices, signatures, QR codes, table of contents, headers/footers/page numbers,
dynamic variables, conditional sections.

## AI-Enhanced Reports

`ReportBuilder(ai_assistant=...)` injects the AI Assistant; default stub keeps
reports working standalone. Sections: summary, insights, trend explanation, root
cause, recommendations, risk assessment, forecast interpretation, action items —
all with citations.

## Export

10 formats via `export_report(report, html, fmt, path)`. Formatting consistency:
HTML is canonical; PDF (reportlab), DOCX (python-docx), XLSX (openpyxl), PPTX
(python-pptx) used when installed, else HTML-placeholder + `degraded: True` flag.

## Scheduling / Distribution / Versioning / Permissions

- Scheduler: cron + intervals, `due_schedules()`, `record_run()` with retry
  backoff, holiday skips.
- Distribution: `deliver_download/email`, `create_shared_link/resolve/revoke`.
- Versions: immutable snapshots, compare (added/removed/changed), restore, approve,
  archive.
- Permissions: `PermissionChecker.require(report, action, user)`; share grants
  per user/role/department/org.

## APIs (`/reports`, 20 endpoints)

CRUD + list/search, `POST /generate`, `POST /preview`, `GET download`,
versions list/compare/restore, approve, archive, share, schedules
(create/cancel/pause/resume), templates (create/list/approve), history, deliveries.

## Testing

`backend/app/reports/tests/test_reporting.py` – 15 tests covering templates,
builder, rendering, all stdlib exports, scheduler, permissions, distribution,
events, service generation, search/compare. Run:
`PYTHONPATH=backend python3 -m pytest backend/app/reports/tests/ -q`.

## Definition of Done

- [x] Dynamic generation via builder + service
- [x] Templates with versioning/approval
- [x] AI summaries with citations plumbed through
- [x] 10 export formats (graceful degradation documented)
- [x] Scheduling with retry/pause/resume
- [x] Secure distribution (signed URLs, link TTL/revoke, delivery tracking)
- [x] Versioning (immutable, compare, restore, approve, archive)
- [x] Permissions enforced in service layer
- [x] Interactive-report primitives (filters/variables, conditional sections, TOC, links)
- [x] APIs implemented (OpenAPI via FastAPI)
- [x] Tests pass (15/15)
- [x] Docs complete

Out of scope per spec: Notification System, Monitoring Platform, DevOps modules.
