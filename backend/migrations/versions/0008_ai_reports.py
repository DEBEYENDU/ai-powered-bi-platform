"""0008 AI reports — ai_reports, ai_report_versions, ai_report_schedules

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_reports",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", PG_UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("owner_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("report_type", sa.String(50), server_default="custom", index=True),
        sa.Column("status", sa.String(50), server_default="pending", index=True),
        sa.Column("dashboard_id", sa.String(255), nullable=True),
        sa.Column("executive_summary", sa.Text, server_default=""),
        sa.Column("sections", JSON, nullable=False, server_default="[]"),
        sa.Column("kpis", JSON, nullable=False, server_default="[]"),
        sa.Column("charts", JSON, nullable=False, server_default="[]"),
        sa.Column("insights", JSON, nullable=False, server_default="[]"),
        sa.Column("risks", JSON, nullable=False, server_default="[]"),
        sa.Column("recommendations", JSON, nullable=False, server_default="[]"),
        sa.Column("branding", JSON, nullable=False, server_default="{}"),
        sa.Column("tags", JSON, nullable=False, server_default="[]"),
        sa.Column("current_version", sa.Integer, server_default="1"),
        sa.Column("generation_time_ms", sa.Float, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "ai_report_versions",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", PG_UUID(as_uuid=True), sa.ForeignKey("ai_reports.id"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("content_snapshot", JSON, nullable=False, server_default="{}"),
        sa.Column("formats_generated", JSON, nullable=False, server_default="[]"),
        sa.Column("storage_paths", JSON, nullable=False, server_default="{}"),
        sa.Column("change_note", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "ai_report_schedules",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", PG_UUID(as_uuid=True), sa.ForeignKey("ai_reports.id"), nullable=False, index=True),
        sa.Column("frequency", sa.String(50), server_default="daily"),
        sa.Column("cron_expression", sa.String(100), server_default=""),
        sa.Column("timezone", sa.String(64), server_default="UTC"),
        sa.Column("recipients", JSON, nullable=False, server_default="[]"),
        sa.Column("formats", JSON, nullable=False, server_default="[\"pdf\"]"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("ai_report_schedules")
    op.drop_table("ai_report_versions")
    op.drop_table("ai_reports")
