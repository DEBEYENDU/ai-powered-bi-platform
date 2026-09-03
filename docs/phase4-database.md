# Phase 4 – Database Design & Data Architecture

> **Implementation Status (as of 2026-09-03):** 4 of ~17 planned entities implemented
> as SQLAlchemy models. No Alembic migrations, no RLS, no star-schema facts yet.

## Database Technology

PostgreSQL with SQLAlchemy 2.x, Alembic migrations (planned – migrations not yet in repo).

## Design Principles

3NF/BCNF, Referential Integrity, Auditability, Soft Deletes, Versioning, Row Level
Security for multi-tenancy (RLS not yet implemented).

## Entities: Planned vs Implemented

| Entity | Status | Location |
|---|---|---|
| organizations | ✅ Implemented | `backend/app/iam/models/user.py` (`Organization`: id, name, slug, created_at) |
| users | ✅ Implemented | `backend/app/iam/models/user.py` (`User`: organization_id, email, password_hash, full_name, is_active, is_verified, created_at, last_login_at, failed_login_count) |
| datasets | ✅ Implemented | `backend/app/dataset/models/dataset.py` (`Dataset` + `DatasetStatus`: DRAFT/UPLOADED/VALIDATED/PROCESSING/PROCESSED/PUBLISHED/ARCHIVED/DELETED; checksum, storage_path, row/column counts, soft delete) |
| etl_jobs | ✅ Implemented | `backend/app/etl/models/job.py` (`ETLJob` + `JobStatus`: PENDING/RUNNING/SUCCESS/FAILED/CANCELLED) |
| roles | ❌ Missing | Planned |
| permissions | ❌ Missing | Planned |
| audit_logs | ❌ Missing (table) | AI audit is in-memory only (`ai/governance/audit.py`) |
| data_sources | ❌ Missing | Planned |
| dataset_versions | ❌ Missing | Planned |
| uploaded_files | ❌ Missing | Planned |
| dashboards | ❌ Missing | Planned (Phase 11) |
| dashboard_widgets | ❌ Missing | Planned (Phase 11) |
| forecast_models | ❌ Missing | Planned (Phase 12) |
| model_versions | ❌ Missing | Planned (Phase 12) |
| predictions | ❌ Missing | Planned (Phase 12) |
| ai_conversations | ❌ Missing (table) | Conversation memory is in-memory (`ai/memory/memory.py`); needs persistence |
| ai_messages | ❌ Missing (table) | Same as above |
| reports | ❌ Missing | Planned |

Vector embeddings: currently in-memory (`ai/vectorstore/vectorstore.py` pgvector
abstraction with in-memory fallback) – pgvector table migration still to be written.

## Schema Highlights (Target – Partially Applied)

* UUID PKs across tables ✅ (applied in all 4 implemented models)
* JSONB for flexible configs (planned; AI cache/metadata uses dicts in memory)
* GIN indexes on JSONB ❌ (no migrations yet)
* Composite indexes for filtering ❌ (no migrations yet)
* Audit fields `created_at`, `updated_at`, `deleted_at` ✅ (present on `Dataset`; partial elsewhere)

## Multi-Tenancy

Target: shared database, shared schema with `tenant_id` + RLS.
Current: `organization_id` FKs present on `User`, `Dataset`, `ETLJob`; vector store and
AI memory enforce org isolation in code; DB-level RLS not implemented.

## Analytics Model (Planned, Not Implemented)

Star schema with fact tables `sales_fact`, `inventory_fact` and dimensions `dim_date`,
`dim_customer`, `dim_product`.

## Next Steps

1. Add `app/db` (Base, engine, `get_db`) + Alembic + initial migration for the 4 existing models.
2. Add missing tables in dependency order: roles/permissions → audit_logs → dataset_versions/uploaded_files → ai_conversations/ai_messages → dashboards → ML tables → reports.
3. Add pgvector extension + embeddings table migration.
4. Add RLS policies per tenant.
