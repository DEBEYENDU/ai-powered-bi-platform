# Phase 5 - API Contract Design

## Tech Stack
FastAPI, Pydantic v2, OpenAPI 3.1

## API Principles
RESTful, Stateless, Versioned /api/v1, Idempotent, JSON only, RFC7807 errors, Pagination, Filtering, Sorting

## Standard Response
Success: { data, meta }
Error: Problem Details with trace_id

## Key Endpoints
Auth: /auth/register, /auth/login, /auth/refresh, /auth/me
Users: /users CRUD, invite, roles
Organizations: /organizations CRUD
Datasets: /datasets upload, status, preview, versions
ETL: /etl/jobs
Dashboards: /dashboards CRUD, widgets
Analytics: /analytics/revenue, sales, top-products
ML: /ml/models train, predict, metrics
AI: /ai/chat, /ai/conversations, /ai/insights, /ai/nlq
Reports: /reports generate, schedule, download

## Security
JWT Access 15min + Refresh 7 days, RBAC, Rate limiting, CORS

## Async Operations
Model training, report generation → 202 Accepted with job_id

OpenAPI spec ready for implementation.
