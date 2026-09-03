# Phase 2 – Software Architecture

> **Implementation Status (as of 2026-09-03):** Modular-monolith layout adopted.
> 5 backend modules exist under `backend/app/` (`iam`, `dataset`, `etl`, `analytics`, `ai`).
> API gateway, frontend, dashboard/ML/reporting services, and shared infrastructure
> (`core`, `db`, `main.py`) are planned but not yet implemented.

## Architecture Style

Modular Monolith with service boundaries, ready to evolve to Microservices.

## High Level Components (Planned)

Frontend React, API Gateway, Auth Service, Ingestion Service, ETL Service, Analytics
Service, ML Engine, AI Engine, Dashboard Service, Reporting Service, PostgreSQL, Redis,
Object Storage.

## Actually Implemented (Current)

```
backend/app/
├── core/         # config, security, logging
├── db/           # Base, lazy engine/session, get_db
├── api/          # /api/v1 aggregation + legacy aliases
├── main.py       # entrypoint (uvicorn app.main:app)
├── middleware/ dependencies/ exceptions/ cache/ workers/
├── repositories/ # BaseRepository
├── services/     # BaseService
├── iam/          # 5 files – models, schemas, repo, service, router
├── dataset/      # 4 files – model, schemas, router, storage base
├── etl/          # 10 files – engine, models, stages, validators, router
├── analytics/    # 7 files – KPI definitions, calculators, schemas, router, cache
├── reports/      # 36 files – builder, templates, exporters, scheduler, routers
└── ai/           # 64+ files – orchestrator, agents, RAG, tools, memory, MCP, governance
```

* Total: ~150 Python files. Shared foundation (`core`/`db`/`api`/`main.py`) landed.
* Infra: `pyproject.toml`, `requirements.txt`, `.env.example`, Alembic + `0001_initial`,
  `Dockerfile`, `docker-compose.yml` (pgvector PG16 + redis + worker).
* No `frontend/` directory yet.
* AI module is the most complete; it orchestrates the other four modules without
  duplicating their logic (`backend/app/ai/services/ai_service.py` facade,
  `backend/app/ai/orchestrator/orchestrator.py` pipeline).

## Design Principles

Modular, Clean Architecture, SOLID, DDD, Separation of Concerns, Dependency Injection,
Secure by Design, API First.

* Applied: repository pattern (`iam/repositories/user_repo.py`), service layer
  (`iam/services/auth_service.py`), storage abstraction (`dataset/storage/base.py`),
  pipeline abstraction (`etl/engine/pipeline.py`, `analytics/engine/pipeline.py`),
  tool registry abstraction (`ai/tools/registry.py`).
* Pending: shared DI wiring (`dependencies/`), centralized config (`core/config.py`),
  app entrypoint (`main.py`) that mounts all routers.

## Module Status

| Module | Status | Notes |
|---|---|---|
| Authentication / IAM | ✅ Partial | Register/login + JWT; roles/permissions tables missing |
| Dataset Management | ✅ Partial | CRUD + upload/preview; versioning missing |
| ETL Pipeline | ✅ Partial | 4 stages + quality engine; cleaners/transformers are placeholders |
| Analytics Engine | ✅ Partial | KPI calc endpoint; 2 of 15 calculators implemented |
| AI Insight Engine | ✅ Implemented | Phase 13 complete (see `docs/phase13-ai-assistant.md`) |
| Dashboard Engine | ❌ Missing | No backend module, no frontend |
| ML Engine | ⚠️ Skeleton | Forecast/predict tools are rule-based placeholders |
| Reporting Engine | ⚠️ Skeleton | Report tool + schemas only |
| Audit Service | ⚠️ Partial | In-memory AI audit log; no persistent audit table |
| API Gateway / Frontend | ❌ Missing | Direct FastAPI routers only (no gateway, no UI) |

## Deployment (Planned, Not Yet Implemented)

Docker + Docker Compose, Nginx LB, FastAPI backend, React frontend static.
No `Dockerfile` / `docker-compose.yml` in repo yet.

## Next Steps

1. Add `app/core`, `app/db`, `app/main.py` + Alembic migrations (Phase 6 gaps).
2. Add packaging/infra files (`pyproject.toml`, `Dockerfile`, `docker-compose.yml`).
3. Implement Dashboard backend, then ML model backend, then frontend.
