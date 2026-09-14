"""AI Dashboard versions table.

Revision ID: 0007_ai_dashboard
Revises: 0006_ai_chat
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_ai_dashboard"
down_revision = "0006_ai_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_dashboard_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "dashboard_id",
            sa.String(36),
            sa.ForeignKey("dashboards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("widgets", sa.JSON, nullable=True),
        sa.Column("layout", sa.JSON, nullable=True),
        sa.Column("filters", sa.JSON, nullable=True),
        sa.Column("theme", sa.JSON, nullable=True),
        sa.Column("prompt", sa.Text, server_default=""),
        sa.Column("change_summary", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_ai_dashboard_versions_dashboard_id",
        "ai_dashboard_versions",
        ["dashboard_id"],
    )


def downgrade() -> None:
    op.drop_table("ai_dashboard_versions")
