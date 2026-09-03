# Phase 5 – API Contract Design

> **Implementation Status (as of 2026-09-03):** 9 endpoints implemented across 5 routers.
> No versioned prefix (`/api/v1`), no pagination/filtering standards, no RFC7807 errors yet.

## Tech Stack

FastAPI, Pydantic v2, OpenAPI 3.1 (FastAPI auto-docs available once `app/main.py` mounts routers).

## API Principles (Target)

RESTful, Stateless, Versioned `/api/v1`, Idempotent, JSON only, RFC7807 errors,
Pagination, Filtering, Sorting. **Current gap:** routers use unversioned prefixes
(`/auth`, `/datasets`, `/etl`, `/analytics`, `/ai`); standards to be applied when
`app/api` aggregation + `app/main.py` are created.

## Standard Response (Target)

Success: `{ data, meta }` · Error: Problem Details with `trace_id`. **Current gap:**
routers return plain Pydantic models.

## Endpoints: Planned vs Implemented

| Area | Endpoint | Status | Location |
|---|---|---|---|
| Auth | `POST /auth/register` | ✅ | `backend/app/iam/routers/auth.py` |
| Auth | `POST /auth/login` | ✅ | `backend/app/iam/routers/auth.py` |
| Auth | `/auth/refresh`, `/auth/me` | ❌ | Planned |
| Users | `/users` CRUD, invite, roles | ❌ | Planned |
| Organizations | `/organizations` CRUD | ❌ | Planned |
| Datasets | `POST /datasets/` (create) | ✅ | `backend/app/dataset/routers/dataset.py` |
| Datasets | `POST /datasets/{id}/upload` | ✅ | `backend/app/dataset/routers/dataset.py` |
| Datasets | `GET /datasets/{id}/preview` | ✅ | `backend/app/dataset/routers/dataset.py` |
| Datasets | `GET /datasets/` (list) | ✅ | `backend/app/dataset/routers/dataset.py` |
| Datasets | status, versions | ❌ | Planned |
| ETL | `POST /etl/jobs` | ✅ | `backend/app/etl/routers/etl.py` |
| ETL | `GET /etl/jobs/{job_id}` | ✅ | `backend/app/etl/routers/etl.py` |
| Analytics | `POST /analytics/kpi/calculate` | ✅ | `backend/app/analytics/routers/analytics.py` |
| Analytics | `/analytics/revenue`, `/sales`, `/top-products` | ❌ | Planned (only internal tools exist) |
| ML | `/ml/models` train/predict/metrics | ❌ | Planned (placeholder tools only) |
| AI | `POST /ai/chat` | ✅ | `backend/app/ai/routers/ai_assistant.py` |
| AI | `POST /ai/nlq` | ✅ | `backend/app/ai/routers/ai_assistant.py` |
| AI | insights, executive-summary, recommendations, root-cause-analysis, prompt-templates, health, feedback, usage-statistics, citations, history/search, suggested-questions | ✅ | `backend/app/ai/routers/ai_assistant.py` (14 routes) |
| AI | `/ai/conversations` persistence | ❌ | In-memory only |
| Dashboards | `/dashboards` CRUD, widgets | ❌ | Planned (Phase 11) |
| Reports | `/reports` generate/schedule/download | ❌ | Planned (tool skeleton only) |

**Implemented total:** 2 (auth) + 4 (datasets) + 2 (etl) + 1 (analytics) + 14 (ai) = 23 routes.

## Security (Target vs Current)

Target: JWT Access 15 min + Refresh 7 days, RBAC, rate limiting, CORS.
Current: JWT access/refresh creation on login (`iam/services/auth_service.py`); refresh/me
endpoints, RBAC middleware, rate limiting, and CORS wiring pending `app/main.py` + middleware.

## Async Operations (Target)

Model training, report generation → `202 Accepted` with `job_id`.
Current: ETL job pattern (`POST /etl/jobs` → poll `GET /etl/jobs/{id}`) follows this;
ML/report async jobs not yet built.

## Next Steps

1. Create `app/main.py` + `app/api` aggregation; mount all 5 routers; enable OpenAPI docs.
2. Add `/api/v1` versioning, response envelope, RFC7807 errors, pagination.
3. Implement missing routers in order: users/organizations → dashboard → ml → reports.
4. Wire auth dependencies (current-user, org scoping) and middleware.
