# Production Completion Pass

Date: 2026-09-06. Goal: every feature functional, persisted, and integrated.

## Backend
- **Persistence**: new `admin/repositories/db_store.py` adapter — DB-first with
  30s-cached availability probe and in-memory fallback, so tests and DB-less
  dev keep working. Wired into users, orgs, RBAC, audit (hash chain preserved
  across restarts), flags (incl. kill state), settings + maintenance windows,
  alerts, notifications, sessions, keys, login history.
- **Users**: `username`, `suspended`, `updated_at` columns (migration 0003);
  `login_history` table; org `owner_id` (0003); flag `killed` (0004).
- **RBAC**: 13 resources × actions matrix (`resource.action`), legacy
  `resource:action` codes accepted via expansion (back-compat), system-role
  protection, clone/edit/grant/revoke/role-users endpoints.
- **Dashboards** (new module + migration 0005): validated widget vocabulary,
  CRUD, share, archive/restore, counts; mounted at `/api/v1/dashboards`.
- **New admin endpoints**: user activate/deactivate/move/change-role/roles,
  role detail/edit/clone/users/grant/revoke/matrix, org archive/users,
  audit CSV+JSON export, alert edit, flag delete, AI overview/prompts/
  vectorstore, job retry/cancel (honest 503 without broker).
- **List enrichment**: users carry role names, orgs carry user counts,
  overview carries inventory counts from live `COUNT(*)` queries.

## Frontend (MUI v9 + DataGrid + Recharts)
- Theme with dark/light toggle, AppBar + Drawer layout, shared DataGrid
  tables (pagination/sorting/filter), dialogs, confirms, error/notice banners.
- Rewritten pages: Overview (stat cards, charts, inventory), Users (full CRUD
  + role multi-select + move), Organizations (CRUD, quotas, archive/restore),
  Roles (matrix editor, clone, users), Health (auto-refresh, details),
  Metrics (auto-refresh, charts, Prometheus link), Audit (filters, date
  range, CSV/JSON export), Alerts (rules + incidents), Flags (CRUD, kill,
  evaluate), Settings (grouped, validated, maintenance), Jobs (live tasks,
  cancel, retry), Reports (create/generate/download), Dashboards (widget
  JSON editor), AI Admin (models, prompts, vectors, monitoring).

## Verification
- Backend 68+ tests pass (incl. new RBAC/dashboard suites), ruff + mypy clean.
- Frontend `tsc` build + vitest pass, `npm audit` 0 high+.
- Live spot-checks: dashboard CRUD, role edit/clone, audit export, AI
  overview, maintenance matrix — all 200.
- Known limits: multi-worker deployments need Redis-backed shared state;
 Celery task history needs a result backend; Node 26 held at 24.
