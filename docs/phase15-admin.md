# Phase 15 – Enterprise Administration, Monitoring & Platform Management

## Overview

Operational backbone: user/org administration, RBAC, feature flags, settings,
health, metrics (Prometheus exposition), tracing, structured logging, immutable
audit log, alert engine, job monitoring, notifications, maintenance mode — plus
a React admin dashboard. Reuses IAM, AI, reports, and infra; no logic duplicated.

## Module Structure (`backend/app/admin/`)

| Package | Implementation |
|---|---|
| users / organizations | `services/users.py`, `services/organizations.py` – lifecycle, suspend, force-reset, sessions, API keys (hashed), login history, quotas, branding |
| roles / permissions | `services/rbac.py` – 4 seeded system roles, 20 permissions in 8 groups, custom roles, simulator |
| settings | `services/settings.py` – validated keys, maintenance windows, override tokens |
| feature_flags | `services/feature_flags.py` – boolean/percentage/org/user/env/scheduled/dependency rules, kills, versioned history |
| monitoring / metrics | `services/metrics.py` – collector, `render_prometheus()`, system + cross-module snapshots |
| logging | Reused `app.core.logging` (structlog JSON / stdlib fallback) |
| tracing | `services/tracing.py` – correlation IDs, nested spans, OTel-compatible shape |
| alerts | `services/alerts.py` – `> < >= <= == !=` rules, deduped firing, ack, auto-resolve, notify fan-out |
| notifications | `services/notifications.py` – in-app inbox (email/SMS is a future phase) |
| audit | `services/audit.py` – append-only, hash-chained, `verify_chain` tamper check |
| health | `services/health.py` – 10 engine checks (db/redis/storage/etl/analytics/ai/ml/reporting/scheduler/workers) |
| jobs | `services/jobs.py` – Celery inspect with clean degradation |
| ai/ml/analytics/dashboards/reports | Status reuse via existing services (no new logic) |
| scheduler | Due-count visibility into reports `Scheduler` |
| middleware | `MaintenanceMiddleware` (off/readonly/maintenance + `X-Admin-Override`) |
| routers | 50+ endpoints under `/admin` (also mounted at `/api/v1/admin`) |
| models | 14 tables in migration `0002_admin` |

## React Dashboard (`frontend/`)

Vite + React 19 + TS + React Router. 11 pages (Overview, Users, Organizations,
Roles, Health, Metrics, Audit, Alerts, Jobs, Flags, Settings) mapped 1:1 to
`/api/v1/admin` endpoints, dev proxy to `:8000`. Run: `npm install && npm run dev`.

## APIs (selected)

- Dashboard: `GET /admin/overview`, `GET /admin/status`
- Users: CRUD, suspend/unsuspend, restore, reset-password, sessions, api-keys, activity
- Orgs: CRUD, suspend/restore, quotas, settings
- RBAC: roles, permissions, assign/unassign, check, simulate
- Flags: CRUD-equivalent, evaluate, kill, history
- Settings/maintenance: get/patch, mode, override-token
- Health/metrics/traces: aggregate health, snapshots, Prometheus text, record, traces
- Audit: query, verify-chain
- Alerts: rules CRUD, incidents, ack, evaluate
- Jobs/scheduler, notifications CRUD

## Testing

`backend/app/admin/tests/test_admin.py` – 21 tests (audit chain + tamper,
RBAC, flags incl. stable bucketing, settings validation, maintenance, health,
Prometheus, tracing, alerts lifecycle, users/orgs, platform, jobs, notifications).
Run: `PYTHONPATH=backend python3 -m pytest backend/app/admin/tests backend/app/reports/tests -q`
→ 36 passed.

## Definition of Done

- [x] User/org administration with quotas
- [x] Roles/permissions + simulator
- [x] Feature flags (all rollout types, kills, history)
- [x] Health monitoring (10 engines)
- [x] Metrics + Prometheus exposition
- [x] Tracing (correlation IDs, spans)
- [x] Structured logging (reused)
- [x] Immutable audit log + verification
- [x] Alert engine (configurable thresholds)
- [x] Job monitoring (graceful degradation)
- [x] AI/ML/analytics monitoring via existing services
- [x] Security monitoring primitives (login history, permission checks, audit)
- [x] Maintenance mode (3 modes + override)
- [x] React dashboard scaffold
- [x] APIs + tests + docs

Out of scope per spec: CI/CD, Kubernetes, IaC, backup/restore automation, cloud deployment.
