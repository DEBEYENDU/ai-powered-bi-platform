"""Initial schema: organizations, users, datasets, etl_jobs, reports suite.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("organization_id", sa.String(),
                  sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("failed_login_count", sa.Integer(), nullable=True),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("organization_id", sa.String(), nullable=False, index=True),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("status", sa.Enum("DRAFT", "UPLOADED", "VALIDATED", "PROCESSING",
                                    "PROCESSED", "PUBLISHED", "ARCHIVED", "DELETED",
                                    name="datasetstatus"), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("column_count", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("storage_path", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "etl_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("dataset_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False, index=True),
        sa.Column("status", sa.Enum("PENDING", "RUNNING", "SUCCESS", "FAILED",
                                    "CANCELLED", name="jobstatus"), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("records_processed", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    # -- reports suite (Phase 14) --
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("report_type", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dashboard_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("definition", sa.JSON(), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "report_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("reports.id"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("definition_snapshot", sa.JSON(), nullable=True),
        sa.Column("rendered_formats", sa.JSON(), nullable=True),
        sa.Column("storage_paths", sa.JSON(), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "report_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("layout", sa.JSON(), nullable=True),
        sa.Column("sections", sa.JSON(), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=True),
        sa.Column("approved", sa.Boolean(), nullable=True),
        sa.Column("shared", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "report_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("reports.id"), nullable=False, index=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("frequency", sa.String(50), nullable=True),
        sa.Column("cron_expression", sa.String(100), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=True),
        sa.Column("max_retries", sa.Integer(), nullable=True),
        sa.Column("distribution", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "report_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("reports.id"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(50), nullable=True),
        sa.Column("recipient", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("execution_time_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "report_shares",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("reports.id"), nullable=False, index=True),
        sa.Column("granted_to", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=True),
        sa.Column("can_export", sa.Boolean(), nullable=True),
        sa.Column("can_distribute", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    # NOTE: pgvector extension + embeddings table arrive in a follow-up
    # migration once the vector backend is finalized.


def downgrade() -> None:
    for table in ("report_shares", "report_deliveries", "report_schedules",
                  "report_templates", "report_versions", "reports",
                  "etl_jobs", "datasets", "users", "organizations"):
        op.drop_table(table)
