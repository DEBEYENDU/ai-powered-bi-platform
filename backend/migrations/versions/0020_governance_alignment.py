"""Align governance tables with the application models.

Revision ID: 0020
Revises: 0019
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # governance_policies
    op.add_column("governance_policies", sa.Column("resource", sa.String(50), server_default="dataset", nullable=False))
    op.add_column("governance_policies", sa.Column("subject_type", sa.String(50), server_default="role", nullable=False))
    op.add_column("governance_policies", sa.Column("subject_id", sa.String(36), server_default="", nullable=False))
    op.add_column("governance_policies", sa.Column("created_by", sa.String(36), server_default="", nullable=False))

    # governance_classifications
    op.add_column("governance_classifications", sa.Column("classified_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.add_column("governance_classifications", sa.Column("expires_at", sa.DateTime(), nullable=True))

    # governance_security_events
    op.add_column("governance_security_events", sa.Column("action", sa.String(100), server_default="", nullable=False))
    op.add_column("governance_security_events", sa.Column("actor_email", sa.String(255), server_default="", nullable=False))
    op.add_column("governance_security_events", sa.Column("actor_id", sa.String(36), server_default="", nullable=False))
    op.add_column("governance_security_events", sa.Column("details", JSON, nullable=True))
    op.add_column("governance_security_events", sa.Column("outcome", sa.String(20), server_default="denied", nullable=False))
    op.add_column("governance_security_events", sa.Column("request_id", sa.String(36), server_default="", nullable=False))
    op.add_column("governance_security_events", sa.Column("source_ip", sa.String(45), server_default="", nullable=False))

    # governance_retention_policies
    op.add_column("governance_retention_policies", sa.Column("auto_delete", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("governance_retention_policies", sa.Column("created_by", sa.String(36), server_default="", nullable=False))
    op.add_column("governance_retention_policies", sa.Column("legal_hold", sa.Boolean(), server_default=sa.text("false"), nullable=False))

    # governance_share_permissions
    op.add_column("governance_share_permissions", sa.Column("permissions", JSON, nullable=True))
    op.add_column("governance_share_permissions", sa.Column("share_type", sa.String(20), server_default="user", nullable=False))
    op.add_column("governance_share_permissions", sa.Column("shared_by", sa.String(36), server_default="", nullable=False))

    # governance_access_reviews
    op.add_column("governance_access_reviews", sa.Column("notes", sa.Text(), server_default="", nullable=False))
    op.add_column("governance_access_reviews", sa.Column("permissions", JSON, nullable=True))
    op.add_column("governance_access_reviews", sa.Column("resource_access", JSON, nullable=True))
    op.add_column("governance_access_reviews", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("governance_access_reviews", sa.Column("reviewed_by", sa.String(36), server_default="", nullable=False))
    op.add_column("governance_access_reviews", sa.Column("roles", JSON, nullable=True))
    op.add_column("governance_access_reviews", sa.Column("user_id", sa.String(36), server_default="", nullable=False))
    op.create_index("ix_governance_access_reviews_user_id", "governance_access_reviews", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_governance_access_reviews_user_id", table_name="governance_access_reviews")
    op.drop_column("governance_access_reviews", "user_id")
    op.drop_column("governance_access_reviews", "roles")
    op.drop_column("governance_access_reviews", "reviewed_by")
    op.drop_column("governance_access_reviews", "reviewed_at")
    op.drop_column("governance_access_reviews", "resource_access")
    op.drop_column("governance_access_reviews", "permissions")
    op.drop_column("governance_access_reviews", "notes")
    op.drop_column("governance_share_permissions", "shared_by")
    op.drop_column("governance_share_permissions", "share_type")
    op.drop_column("governance_share_permissions", "permissions")
    op.drop_column("governance_retention_policies", "legal_hold")
    op.drop_column("governance_retention_policies", "created_by")
    op.drop_column("governance_retention_policies", "auto_delete")
    op.drop_column("governance_security_events", "source_ip")
    op.drop_column("governance_security_events", "request_id")
    op.drop_column("governance_security_events", "outcome")
    op.drop_column("governance_security_events", "details")
    op.drop_column("governance_security_events", "actor_id")
    op.drop_column("governance_security_events", "actor_email")
    op.drop_column("governance_security_events", "action")
    op.drop_column("governance_classifications", "expires_at")
    op.drop_column("governance_classifications", "classified_at")
    op.drop_column("governance_policies", "created_by")
    op.drop_column("governance_policies", "subject_id")
    op.drop_column("governance_policies", "subject_type")
    op.drop_column("governance_policies", "resource")
