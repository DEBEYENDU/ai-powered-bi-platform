"""Add multi-tenant infrastructure: plan, subscription, usage, API keys, config.

Revision ID: 0017
Revises: 0016
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend organizations
    op.add_column("organizations", sa.Column("status", sa.String(20), server_default="active", nullable=False))
    op.add_column("organizations", sa.Column("plan", sa.String(50), server_default="free", nullable=False))
    op.add_column("organizations", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.add_column("organizations", sa.Column("suspended_at", sa.DateTime(), nullable=True))

    # Plans
    op.create_table(
        "plans",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("max_users", sa.Integer(), server_default="5"),
        sa.Column("max_datasets", sa.Integer(), server_default="10"),
        sa.Column("max_storage_mb", sa.Integer(), server_default="500"),
        sa.Column("max_queries_per_minute", sa.Integer(), server_default="60"),
        sa.Column("max_concurrent_queries", sa.Integer(), server_default="5"),
        sa.Column("max_ai_requests", sa.Integer(), server_default="100"),
        sa.Column("max_ai_tokens", sa.Integer(), server_default="50000"),
        sa.Column("max_workflows", sa.Integer(), server_default="5"),
        sa.Column("max_reports", sa.Integer(), server_default="10"),
        sa.Column("max_dashboards", sa.Integer(), server_default="10"),
        sa.Column("max_rag_documents", sa.Integer(), server_default="50"),
        sa.Column("max_rag_storage_mb", sa.Integer(), server_default="100"),
        sa.Column("max_predictions", sa.Integer(), server_default="20"),
        sa.Column("max_api_keys", sa.Integer(), server_default="5"),
        sa.Column("price_monthly", sa.Float(), server_default="0.0"),
        sa.Column("price_yearly", sa.Float(), server_default="0.0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # Subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("organization_id", sa.String(255), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("plan_id", sa.String(255), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default="trialing"),
        sa.Column("provider", sa.String(50), server_default="local"),
        sa.Column("external_subscription_id", sa.String(255), nullable=True),
        sa.Column("starts_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("trial_ends_at", sa.DateTime(), nullable=True),
        sa.Column("canceled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # Usage records
    op.create_table(
        "usage_records",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("organization_id", sa.String(255), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("resource_type", sa.String(50), nullable=False, index=True),
        sa.Column("quantity", sa.Integer(), server_default="1"),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("request_id", sa.String(255), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_usage_org_resource", "usage_records", ["organization_id", "resource_type"])

    # Tenant API keys
    op.create_table(
        "tenant_api_keys",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("organization_id", sa.String(255), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_hash", sa.String(255), unique=True, nullable=False),
        sa.Column("key_prefix", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("scopes", sa.Text(), server_default="*"),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Tenant configurations
    op.create_table(
        "tenant_configurations",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("organization_id", sa.String(255), sa.ForeignKey("organizations.id"), unique=True, nullable=False, index=True),
        sa.Column("timezone", sa.String(50), server_default="UTC"),
        sa.Column("locale", sa.String(10), server_default="en"),
        sa.Column("branding_json", sa.Text(), nullable=True),
        sa.Column("ai_preferences_json", sa.Text(), nullable=True),
        sa.Column("retention_days", sa.Integer(), server_default="365"),
        sa.Column("custom_settings_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("tenant_configurations")
    op.drop_table("tenant_api_keys")
    op.drop_index("ix_usage_org_resource", table_name="usage_records")
    op.drop_table("usage_records")
    op.drop_table("subscriptions")
    op.drop_table("plans")
    op.drop_column("organizations", "suspended_at")
    op.drop_column("organizations", "updated_at")
    op.drop_column("organizations", "plan")
    op.drop_column("organizations", "status")