# Admin Platform — Architecture Guide

## Composition

`services/platform.py::PlatformAdmin` owns one instance of every sub-service;
routers depend on `get_platform()`. No business logic is duplicated: user/org
lifecycle wraps IAM shapes, health/metrics probe existing engines, scheduler
status reads the reports `Scheduler`, notifications fan out from alerts.

## Packages

- users/organizations: admin lifecycle (suspend, force-reset, sessions, API keys,
  quotas, branding) around IAM records.
- roles/permissions: RBAC with seeded system roles + custom org roles, simulator.
- settings: validated keys + maintenance windows + override tokens.
- feature_flags: boolean/percentage/org/user/env/scheduled/dependency rules + kills.
- monitoring/metrics: collector, Prometheus exposition, system + platform snapshots.
- logging: `app.core.logging` reuse (structlog JSON or stdlib fallback).
- tracing: correlation IDs + nested spans, OTel-compatible shape.
- alerts: threshold rules, deduped firing, ack, auto-resolve, notify fan-out.
- notifications: in-app inbox (email/SMS is a future Notification System).
- audit: append-only hash-chained log + `verify_chain` tamper check.
- health: per-engine checks (db, redis, storage, etl, analytics, ai, ml,
  reporting, scheduler, workers).
- jobs: Celery inspect with clean degradation.
- ai/ml/analytics/dashboards/reports: status reuse markers (no new logic).
- scheduler: due-count visibility into reports scheduler.
- middleware: maintenance enforcement (off/readonly/maintenance + override).
- cache/events/utils: namespaces, bus, pagination/redaction/license helpers.

## Dependency map (production)

Prometheus scrapes `GET /admin/metrics/prometheus`; Grafana dashboards query it.
OpenTelemetry SDK can consume `Tracer` spans via the recent-traces endpoint.
Logs ship as JSON via structlog. None of these are required to run the API.

## Security

Every mutating endpoint is an audited action. RBAC enforcement point for admin
routes is `PermissionChecker`-equivalent logic in services; organization scoping
via `require_organization`. Secrets (API keys) stored as SHA-256 hashes, raw
value shown once at creation.
