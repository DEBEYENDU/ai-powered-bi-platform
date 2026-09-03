# Phase 1 – Software Requirements Specification

> **Implementation Status (as of 2026-09-03):** Requirements defined. Backend covers IAM,
> Dataset, ETL, Analytics, and AI Assistant (Phases 7–10, 13). Dashboard/ML/Reporting
> backend, frontend, and infrastructure are planned but not yet implemented.
> See status table at the bottom.

## Project Title

AI-Powered Business Intelligence and Analytics Platform

## Goals

Automate business data analysis, generate insights with AI/ML, predict trends, provide
interactive dashboards, enable data-driven decisions.

## Functional Requirements

* Data Ingestion & ETL
* Data Cleaning & Validation
* Dashboard & KPI Monitoring
* Predictive Analytics & Forecasting
* AI Insights & Natural Language Query
* Reporting & Export
* RBAC & Audit

## Non-Functional Requirements

Performance, Availability 99%, Security, Scalability, Usability, Accessibility WCAG 2.1 AA.

Success targets: Prediction MAPE < 20%, Dashboard load < 3s, AI response < 5s, Uptime 99%.

## User Roles

Administrator, Business Owner, Business Analyst, Data Analyst, Manager, Viewer.

## User Stories

50+ detailed user stories covering upload, analysis, forecast, AI chat, reporting.

## Use Cases

Upload & Clean Data, Generate Forecast, NLQ, Create Dashboard, Export Report.

## Requirement Implementation Status

| Requirement | Status | Evidence |
|---|---|---|
| Data Ingestion & ETL | ✅ Partial | `backend/app/etl/` – Extract/Profile/Clean/Transform stages, `ETLJob` model, `/etl/jobs` endpoints |
| Data Cleaning & Validation | ✅ Partial | `CleanStage`, `QualityEngine`, `validators/base.py` (`ValidationRule`, `RequiredRule`) |
| Auth, RBAC & Audit | ✅ Partial | `backend/app/iam/` – register/login, JWT; `backend/app/ai/governance/audit.py` – AI audit trail. Full RBAC/roles tables not yet implemented |
| Dataset Management | ✅ Partial | `backend/app/dataset/` – `Dataset` model, CRUD + upload/preview routers, local storage provider |
| KPI Monitoring | ✅ Partial | `backend/app/analytics/` – 15-KPI definitions, revenue/profit calculators, `/analytics/kpi/calculate` |
| AI Insights & NLQ | ✅ Implemented | `backend/app/ai/` (64 files) – orchestrator, 16-tool registry, RAG, 6 agents, MCP, memory, governance; `POST /ai/chat`, `POST /ai/nlq` |
| Predictive Analytics & Forecasting | ⚠️ Skeleton | `backend/app/ai/tools/ml_tools.py`, `ForecastAgent` – rule-based placeholders; no trained-model backend yet |
| Dashboard & Visualization | ❌ Not implemented | No dashboard backend module, no frontend |
| Reporting & Export | ⚠️ Skeleton | `generate_report` tool + schemas; no Reporting Engine module |
| Frontend (all UX journeys) | ❌ Not implemented | No `frontend/` directory yet |
| Infra (Docker, CI/CD, env) | ❌ Not implemented | No `Dockerfile`, `docker-compose.yml`, `pyproject.toml`, `.env.example` |

**Legend:** ✅ Implemented · ⚠️ Skeleton/placeholder · ❌ Not implemented

## Next Steps (Priority Order)

1. Backend foundation gaps: `app/core` (config/security), `app/db` (engine/session), `app/main.py`, Alembic migrations.
2. Build/packaging: `pyproject.toml`, `.env.example`, `Dockerfile`, `docker-compose.yml`.
3. Dashboard backend + ML model backend (Phases 11–12) to fulfil SRS dashboard/forecast requirements.
4. Frontend (React) for upload → dashboard → forecast → AI chat → export journey.
5. Full RBAC (roles/permissions tables) and audit-log persistence.
