"""User management + org ownership fields.

Revision ID: 0003_users_orgs
Revises: 0002_admin
Create Date: 2026-09-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_users_orgs"
down_revision = "0002_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(150), nullable=True))
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.add_column("users", sa.Column("suspended", sa.Boolean(), nullable=True))
    op.execute("UPDATE users SET suspended = false WHERE suspended IS NULL")
    op.add_column(
        "users", sa.Column("updated_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "organizations",
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column("organizations", sa.Column("suspended", sa.Boolean(), nullable=True))
    op.execute("UPDATE organizations SET suspended = false WHERE suspended IS NULL")
    op.add_column("organizations", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_table(
        "login_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_table("login_history")
    op.drop_column("organizations", "deleted_at")
    op.drop_column("organizations", "suspended")
    op.drop_column("organizations", "owner_id")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "suspended")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "username")
