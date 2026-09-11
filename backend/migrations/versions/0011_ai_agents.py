"""AI Multi-Agent platform tables

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-11
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels: str | tuple | None = None
depends_on: str | tuple | None = None


def upgrade() -> None:
    op.create_table(
        "ai_agent_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", sa.String(50), nullable=False, index=True),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", index=True),
        sa.Column("agent_sequence", postgresql.JSON(), server_default="[]"),
        sa.Column("answer", sa.Text(), server_default=""),
        sa.Column("metrics", postgresql.JSON(), server_default="{}"),
        sa.Column("artifacts", postgresql.JSON(), server_default="[]"),
        sa.Column("context", postgresql.JSON(), server_default="{}"),
        sa.Column("session_id", sa.String(100), server_default=""),
        sa.Column("duration_ms", sa.Float(), server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "ai_agent_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(), default=datetime.utcnow, index=True),
        sa.Column("level", sa.String(20), server_default="info", index=True),
        sa.Column("agent_type", sa.String(50), server_default="", index=True),
        sa.Column("task_id", sa.String(50), server_default="", index=True),
        sa.Column("message", sa.Text(), server_default=""),
        sa.Column("data", postgresql.JSON(), server_default="{}"),
    )

    op.create_table(
        "ai_agent_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("agent_type", sa.String(50), nullable=False, index=True),
        sa.Column("calls", sa.Integer(), server_default="0"),
        sa.Column("successes", sa.Integer(), server_default="0"),
        sa.Column("failures", sa.Integer(), server_default="0"),
        sa.Column("total_duration_ms", sa.Float(), server_default="0"),
        sa.Column("avg_duration_ms", sa.Float(), server_default="0"),
        sa.Column("recorded_at", sa.DateTime(), default=datetime.utcnow, index=True),
    )


def downgrade() -> None:
    op.drop_table("ai_agent_metrics")
    op.drop_table("ai_agent_logs")
    op.drop_table("ai_agent_tasks")
