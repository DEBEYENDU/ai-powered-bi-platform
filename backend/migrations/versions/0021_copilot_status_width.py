"""Widen copilot_tasks.status to VARCHAR(50): 'awaiting_clarification'
(23 chars) exceeded the original VARCHAR(20) and broke the copilot flow.

Revision ID: 0021
Revises: 0020
"""
from alembic import op
import sqlalchemy as sa

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "copilot_tasks", "status", type_=sa.String(50), existing_type=sa.String(20)
    )


def downgrade() -> None:
    op.alter_column(
        "copilot_tasks", "status", type_=sa.String(20), existing_type=sa.String(50)
    )
