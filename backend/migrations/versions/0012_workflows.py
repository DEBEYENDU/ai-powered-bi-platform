"""Workflow automation tables

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-11
"""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels: str | tuple | None = None
depends_on: str | tuple | None = None


def upgrade() -> None:
    op.create_table(
        "workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("status", sa.String(50), server_default="draft", index=True),
        sa.Column("trigger_config", postgresql.JSON(), server_default="{}"),
        sa.Column("steps", postgresql.JSON(), server_default="[]"),
        sa.Column("conditions", postgresql.JSON(), server_default="[]"),
        sa.Column("schedule", postgresql.JSON(), server_default="{}"),
        sa.Column("variables", postgresql.JSON(), server_default="{}"),
        sa.Column("tags", postgresql.JSON(), server_default="[]"),
        sa.Column("is_test", sa.Boolean(), server_default="false"),
        sa.Column("max_retries", sa.Integer(), server_default="3"),
        sa.Column("timeout_seconds", sa.Integer(), server_default="3600"),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "workflow_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_type", sa.String(50), server_default="manual"),
        sa.Column("status", sa.String(50), server_default="running", index=True),
        sa.Column("is_test", sa.Boolean(), server_default="false"),
        sa.Column("input_data", postgresql.JSON(), server_default="{}"),
        sa.Column("output_data", postgresql.JSON(), server_default="{}"),
        sa.Column("errors", postgresql.JSON(), server_default="[]"),
        sa.Column("duration_ms", sa.Float(), server_default="0"),
        sa.Column("idempotency_key", sa.String(100), server_default="", index=True),
        sa.Column("started_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )

    op.create_table(
        "workflow_step_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("step_id", sa.String(100), nullable=False),
        sa.Column("step_name", sa.String(255), server_default=""),
        sa.Column("action_type", sa.String(100), server_default=""),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("input_data", postgresql.JSON(), server_default="{}"),
        sa.Column("output_data", postgresql.JSON(), server_default="{}"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column("max_retries", sa.Integer(), server_default="3"),
        sa.Column("duration_ms", sa.Float(), server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )

    op.create_table(
        "workflow_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("step_id", sa.String(100), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", index=True),
        sa.Column("message", sa.Text(), server_default=""),
        sa.Column("response", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "workflow_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("channel", sa.String(50), server_default="in_app"),
        sa.Column("recipient", sa.String(255), server_default=""),
        sa.Column("subject", sa.String(500), server_default=""),
        sa.Column("body", sa.Text(), server_default=""),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )

    op.create_table(
        "workflow_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("category", sa.String(100), server_default="general", index=True),
        sa.Column("trigger_config", postgresql.JSON(), server_default="{}"),
        sa.Column("steps", postgresql.JSON(), server_default="[]"),
        sa.Column("conditions", postgresql.JSON(), server_default="[]"),
        sa.Column("schedule", postgresql.JSON(), server_default="{}"),
        sa.Column("tags", postgresql.JSON(), server_default="[]"),
        sa.Column("is_system", sa.Boolean(), server_default="false"),
        sa.Column("usage_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
    )


def downgrade() -> None:
    op.drop_table("workflow_templates")
    op.drop_table("workflow_notifications")
    op.drop_table("workflow_approvals")
    op.drop_table("workflow_step_executions")
    op.drop_table("workflow_executions")
    op.drop_table("workflows")
