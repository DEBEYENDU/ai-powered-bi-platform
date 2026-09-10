"""AI Predictions tables

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-10
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels: str | tuple | None = None
depends_on: str | tuple | None = None


def upgrade() -> None:
    # ai_prediction_models
    op.create_table(
        "ai_prediction_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("model_type", sa.String(50), nullable=False, index=True),
        sa.Column("target", sa.String(255), nullable=False),
        sa.Column("dataset_id", sa.String(255), nullable=False, index=True),
        sa.Column("status", sa.String(50), server_default="training", index=True),
        sa.Column("metrics", postgresql.JSON(), server_default="{}"),
        sa.Column("hyperparameters", postgresql.JSON(), server_default="{}"),
        sa.Column("feature_names", postgresql.JSON(), server_default="[]"),
        sa.Column("feature_importances", postgresql.JSON(), server_default="[]"),
        sa.Column("model_path", sa.String(500), server_default=""),
        sa.Column("current_version", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    # ai_predictions
    op.create_table(
        "ai_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("model_id", sa.String(255), nullable=False, index=True),
        sa.Column("dataset_id", sa.String(255), nullable=False, index=True),
        sa.Column("target", sa.String(255), nullable=False),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("horizon", sa.String(50), nullable=False),
        sa.Column("predictions", postgresql.JSON(), server_default="[]"),
        sa.Column("overall_confidence", sa.Float(), server_default="0"),
        sa.Column("trend", sa.String(50), server_default="stable"),
        sa.Column("growth_percentage", sa.Float(), server_default="0"),
        sa.Column("risk_score", sa.Float(), server_default="0"),
        sa.Column("metrics", postgresql.JSON(), server_default="{}"),
        sa.Column("explainability", postgresql.JSON(), server_default="{}"),
        sa.Column("recommendations", postgresql.JSON(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )

    # ai_model_versions
    op.create_table(
        "ai_model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("model_id", sa.String(255), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("metrics", postgresql.JSON(), server_default="{}"),
        sa.Column("hyperparameters", postgresql.JSON(), server_default="{}"),
        sa.Column("model_path", sa.String(500), server_default=""),
        sa.Column("status", sa.String(50), server_default="ready"),
        sa.Column("is_active", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )

    # ai_prediction_drift
    op.create_table(
        "ai_prediction_drift",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("model_id", sa.String(255), nullable=False, index=True),
        sa.Column("drift_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(50), server_default="low"),
        sa.Column("feature", sa.String(255), server_default=""),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("metrics", postgresql.JSON(), server_default="{}"),
        sa.Column("recommended_action", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )

    # ai_scenarios
    op.create_table(
        "ai_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("prediction_id", sa.String(255), nullable=False, index=True),
        sa.Column("scenario_name", sa.String(255), nullable=False),
        sa.Column("scenario_type", sa.String(50), nullable=False),
        sa.Column("variables", postgresql.JSON(), server_default="{}"),
        sa.Column("predicted_impact", postgresql.JSON(), server_default="{}"),
        sa.Column("confidence", sa.Float(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )


def downgrade() -> None:
    op.drop_table("ai_scenarios")
    op.drop_table("ai_prediction_drift")
    op.drop_table("ai_model_versions")
    op.drop_table("ai_predictions")
    op.drop_table("ai_prediction_models")
