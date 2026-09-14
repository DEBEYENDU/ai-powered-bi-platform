"""Autonomous BI Copilot tables

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-13
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels: str | tuple | None = None
depends_on: str | tuple | None = None


def upgrade() -> None:
    op.create_table(
        "copilot_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("message_count", sa.Integer(), server_default="0"),
    )

    op.create_table(
        "copilot_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("copilot_sessions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("request", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="created"),
        sa.Column("intent", sa.String(50), nullable=True),
        sa.Column("intent_confidence", sa.Float(), nullable=True),
        sa.Column("plan_json", sa.Text(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("total_steps", sa.Integer(), server_default="0"),
        sa.Column("completed_steps", sa.Integer(), server_default="0"),
        sa.Column("tools_used", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_copilot_tasks_session", "copilot_tasks", ["session_id"])

    op.create_table(
        "copilot_task_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "task_id",
            sa.String(36),
            sa.ForeignKey("copilot_tasks.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("input_json", sa.Text(), nullable=True),
        sa.Column("output_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("retries", sa.Integer(), server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("copilot_task_steps")
    op.drop_index("ix_copilot_tasks_session", table_name="copilot_tasks")
    op.drop_table("copilot_tasks")
    op.drop_table("copilot_sessions")
