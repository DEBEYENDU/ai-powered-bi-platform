# Phase 6 – Backend Foundation & Core Infrastructure

> **Implementation Status (as of 2026-09-03):** Module-level foundations exist
> (pipelines, repos, services, storage/registry abstractions). **Shared core
> infrastructure is missing**: no `app/core`, `app/db`, `app/main.py`, no migrations,
> no packaging/infra files. This is the highest-priority gap in the project.

## Project Structure: Planned vs Actual

| Planned (`app/...`) | Status | Notes |
|---|---|---|
| `core` (config, security, logger) | ❌ Missing | Highest priority – blocks env config, JWT reuse, logging |
| `db` (engine, session, Base) | ❌ Missing | Models import `app.db.base` which does not exist – app cannot boot |
| `api` (router aggregation) | ❌ Missing | 5 routers exist unmounted |
| `main.py` (app entrypoint) | ❌ Missing | No runnable app |
| `services/` (shared base) | ⚠️ Partial | Only `iam/services/auth_service.py` + `ai/services/ai_service.py`; no `BaseService` |
| `repositories/` (shared base) | ⚠️ Partial | Only `iam/repositories/user_repo.py`; no `BaseRepository` |
| `schemas/` (shared) | ⚠️ Partial | Per-module schemas exist; no shared envelope/errors |
| `models/` (shared) | ⚠️ Partial | Per-module models exist; no shared Base/mixins |
| `middleware/` | ❌ Missing | No CORS, rate-limit, security headers, timing |
| `dependencies/` | ❌ Missing | No `get_db`, current-user/org DI |
| `exceptions/` | ❌ Missing | No handlers |
| `cache/` | ✅ Partial | `analytics/cache.py` (Redis wrapper) + `ai/cache/caching.py` (TTL/LRU); no shared `CacheService` |
| `storage/` | ✅ Partial | `dataset/storage/base.py` (`StorageProvider` + `LocalStorageProvider`); S3/MinIO future |
| `workers/` (Celery) | ❌ Missing | No broker/worker wiring |
| `migrations/` (Alembic) | ❌ Missing | No migrations |

Module-local equivalents that already follow the pattern: `etl/engine/pipeline.py`,
`analytics/engine/pipeline.py`, `etl/stages/registry.py`, `ai/tools/registry.py`,
`ai/mcp/server.py` (plugin registry).

## Configuration (Target, Missing)

Pydantic Settings with `.env`, environment-specific configs, validation.
No `app/core/config.py`, no `.env.example`. AI defaults (models, weights, TTLs) are
hardcoded in constructors (`RAGConfig`, `EmbeddingConfig`, `AICache`).

## Database Foundation (Target, Missing)

Async SQLAlchemy engine, session factory, `get_db` dependency, health check, connection
retry. Models are written against a `Base` that does not exist yet.

## Logging (Partial)

`ai/governance/audit.py` provides structured AI audit events; `ai/monitoring/observability.py`
tracks latency/tokens/cost. No shared structlog/JSON logger, request/correlation IDs.

## Middleware (Missing)

Request logging, timing, auth, rate limiting, CORS, security headers, compression – none
wired (no `main.py`).

## Authentication Foundation (Partial)

JWT creation + bcrypt verification implemented in `iam/services/auth_service.py`;
`SafetyChecker` covers AI input. Missing: shared `core/security.py`, token validation
dependency, RBAC engine, refresh endpoint.

## Caching (Partial)

`analytics/cache.py` + `ai/cache/caching.py` with TTL, eviction, stats, namespaced keys.
Missing: shared Redis connection/`CacheService`, cache invalidation wiring to ETL/dataset writes.

## Background Tasks (Missing)

Celery with Redis broker, retry, dead-letter queue – not wired. ETL jobs are synchronous
stubs; forecast/report tools return rule-based results inline.

## Health Checks (Missing)

`/health` endpoints for app/db/redis/storage – only `GET /ai/health` (static) exists.

## Docker (Missing)

`Dockerfile` + `docker-compose.yml` for api/db/redis/worker – not in repo. Same for
`pyproject.toml`, `.env.example`, `.github/workflows`.

## Next Steps (Priority Order)

1. `app/core/config.py` + `app/core/security.py` + `app/db/base.py` + `app/db/session.py` (`get_db`).
2. `app/main.py` + `app/api/__init__.py` mounting all routers + middleware + exception handlers.
3. `pyproject.toml` (or `requirements.txt`) pinning FastAPI/SQLAlchemy/Pydantic/Redis/pytest + `.env.example`.
4. Alembic init + initial migration (organizations, users, datasets, etl_jobs).
5. `Dockerfile` + `docker-compose.yml` (api, db/postgres+pgvector, redis, worker).
6. Shared `BaseRepository`/`BaseService`, health endpoints, CI workflow.
