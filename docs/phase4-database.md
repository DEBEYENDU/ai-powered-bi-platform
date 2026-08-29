# Phase 4 - Database Design & Data Architecture

## Database Technology
PostgreSQL with SQLAlchemy 2.x, Alembic migrations

## Design Principles
3NF/BCNF, Referential Integrity, Auditability, Soft Deletes, Versioning, Row Level Security for multi-tenancy

## Core Entities
organizations, users, roles, permissions, audit_logs, data_sources, datasets, dataset_versions, uploaded_files, dashboards, dashboard_widgets, forecast_models, model_versions, predictions, ai_conversations, ai_messages, reports

## Schema Highlights
* UUID PKs across tables
* JSONB for flexible configs
* GIN indexes on JSONB
* Composite indexes for filtering
* Audit fields created_at, updated_at, deleted_at

## Multi-Tenancy
Shared database, shared schema with tenant_id + RLS

## Analytics Model
Star schema with fact tables sales_fact, inventory_fact and dimensions dim_date, dim_customer, dim_product

Full data dictionary and ER diagrams available.
