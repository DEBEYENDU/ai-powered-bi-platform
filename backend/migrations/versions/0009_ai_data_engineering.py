"""AI Data Engineering tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-10
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels: str | tuple | None = None
depends_on: str | tuple | None = None


def upgrade() -> None:
    # de_datasets
    op.create_table(
        "de_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("source_type", sa.String(50), server_default="csv"),
        sa.Column("storage_path", sa.String(500), server_default=""),
        sa.Column("row_count", sa.Integer(), server_default="0"),
        sa.Column("column_count", sa.Integer(), server_default="0"),
        sa.Column("file_size", sa.Integer(), server_default="0"),
        sa.Column("schema_info", postgresql.JSON(), server_default="{}"),
        sa.Column("profile", postgresql.JSON(), server_default="{}"),
        sa.Column("quality_score", sa.Float(), server_default="0"),
        sa.Column("current_version", sa.Integer(), server_default="1"),
        sa.Column("tags", postgresql.JSON(), server_default="[]"),
        sa.Column("status", sa.String(50), server_default="uploaded", index=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    # de_dataset_versions
    op.create_table(
        "de_dataset_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(500), server_default=""),
        sa.Column("row_count", sa.Integer(), server_default="0"),
        sa.Column("column_count", sa.Integer(), server_default="0"),
        sa.Column("quality_score", sa.Float(), server_default="0"),
        sa.Column("change_summary", sa.Text(), server_default=""),
        sa.Column("transforms_applied", postgresql.JSON(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )

    # de_pipelines
    op.create_table(
        "de_pipelines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("steps", postgresql.JSON(), server_default="[]"),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("schedule", sa.String(100), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_run_status", sa.String(50), server_default=""),
        sa.Column("run_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    # de_audit_logs
    op.create_table(
        "de_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("dataset_id", sa.String(255), nullable=True, index=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("details", postgresql.JSON(), server_default="{}"),
        sa.Column("user_id", sa.String(255), server_default=""),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )


def downgrade() -> None:
    op.drop_table("de_audit_logs")
    op.drop_table("de_pipelines")
    op.drop_table("de_dataset_versions")
    op.drop_table("de_datasets")
