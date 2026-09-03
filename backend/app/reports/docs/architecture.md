# Reporting Engine — Architecture Guide

## Workflow

```
User Request → Authentication → Permission Validation → Analytics/Dashboard/AI
→ Report Builder → Template Engine → HTML Renderer → Exporters → Storage
→ Distribution → Audit Logging
```

## Packages

- **templates/** — branded layouts, versioning, approval, Jinja2 (+fallback).
- **generators/** — `ReportBuilder`: pulls analytics KPIs, dashboard data, AI
  sections (with citations); conditional sections; per-section fault isolation.
- **renderers/** — canonical HTML (inline CSS); PDF/PNG derive from it.
- **exporters/** — pdf, docx, xlsx, csv, json, html, pptx, png, svg, zip.
  Stdlib formats always work; office/PDF degrade gracefully without optional deps.
- **schedulers/** — one_time/hourly/daily/weekly/monthly/quarterly/yearly/cron,
  timezones, holidays, pause/resume, retries with backoff, max-retry auto-pause.
- **distributions/** — download (signed URLs), email (swappable sender), shared
  links (TTL + revoke), org sharing, webhook hook; delivery attempts tracked.
- **repositories/** — persistence-agnostic store + immutable versions + compare.
- **routers/** — `/reports` CRUD, generate/preview/download, versions,
  approve/archive/restore, share, schedules, templates, history, deliveries.
- **services/** — `ReportService` orchestrates the full workflow + audit.
- **schemas/models** — Pydantic contracts + SQLAlchemy records.
- **jobs/** — Celery-compatible `generate_report_task`, `run_due_schedules_task`
  (sync fallback without broker).
- **cache/permissions/events/utils** — TTL cache, RBAC, event bus, helpers.

## Reuse (no duplication)

- Analytics: KPI definitions via lazy import; dashboard data via injected fetcher.
- AI: `ReportBuilder(ai_assistant=...)` accepts the AI Assistant; default stub
  keeps reports working standalone. AI sections carry citations end-to-end.
- Storage: `storage_root` path injection; dataset storage abstraction reused by convention.
- Notifications: `DistributionEngine(email_sender=...)` accepts the notification sender.

## Security

RBAC per action (view/edit/review/approve/export/distribute/share/delete),
org isolation on listings, signed time-boxed download URLs, checksums,
immutable published versions, full audit trail.
