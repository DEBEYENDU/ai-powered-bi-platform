"""Admin platform tables: audit log, RBAC, flags, settings, alerts, keys.

Revision ID: 0002_admin
Revises: 0001_initial
Create Date: 2026-09-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_admin"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=True, index=True),
        sa.Column("actor_id", sa.String(255), nullable=True, index=True),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("prev_hash", sa.String(64), nullable=True),
        sa.Column("entry_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, index=True),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=True, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("system_role", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(150), nullable=False, unique=True),
        sa.Column("group", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id"),
                  nullable=False, index=True),
        sa.Column("permission_id", sa.String(36), sa.ForeignKey("permissions.id"),
                  nullable=False, index=True),
    )
    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id"),
                  nullable=False, index=True),
        sa.Column("organization_id", sa.String(36), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "feature_flags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key", sa.String(150), nullable=False, unique=True, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("flag_type", sa.String(30), nullable=True),
        sa.Column("default_value", sa.JSON(), nullable=True),
        sa.Column("rules", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(150), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("metric", sa.String(150), nullable=False, index=True),
        sa.Column("operator", sa.String(10), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("window_seconds", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "alert_incidents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("alert_rules.id"),
                  nullable=False, index=True),
        sa.Column("metric", sa.String(150), nullable=True),
        sa.Column("observed_value", sa.Float(), nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, index=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("revoked", sa.Boolean(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "organization_quotas",
        sa.Column("organization_id", sa.String(36), primary_key=True),
        sa.Column("storage_mb", sa.Integer(), nullable=True),
        sa.Column("dataset_limit", sa.Integer(), nullable=True),
        sa.Column("ai_requests_per_day", sa.Integer(), nullable=True),
        sa.Column("api_requests_per_minute", sa.Integer(), nullable=True),
        sa.Column("suspended", sa.Boolean(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "maintenance_windows",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mode", sa.String(30), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("organization_id", sa.String(36), nullable=True, index=True),
        sa.Column("kind", sa.String(50), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("read", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, index=True),
    )


def downgrade() -> None:
    for table in ("notifications", "maintenance_windows", "organization_quotas",
                  "user_sessions", "api_keys", "alert_incidents", "alert_rules",
                  "system_settings", "feature_flags", "user_roles",
                  "role_permissions", "permissions", "roles", "admin_audit_logs"):
        op.drop_table(table)
