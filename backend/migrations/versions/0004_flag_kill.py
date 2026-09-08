"""Feature flag kill-switch persistence.

Revision ID: 0004_flag_kill
Revises: 0003_users_orgs
Create Date: 2026-09-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_flag_kill"
down_revision = "0003_users_orgs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("feature_flags", sa.Column("killed", sa.Boolean(), nullable=True))
    op.execute("UPDATE feature_flags SET killed = false WHERE killed IS NULL")


def downgrade() -> None:
    op.drop_column("feature_flags", "killed")
