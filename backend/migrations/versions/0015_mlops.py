"""MLOps tables

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-13
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels: str | tuple | None = None
depends_on: str | tuple | None = None


def upgrade() -> None:
    op.create_table(
        "mlops_models",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("framework", sa.String(50), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "mlops_model_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_id", sa.String(36), nullable=False, index=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("version_number", sa.String(50), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("artifact_size_bytes", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="created"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )
    op.create_index("ix_mlops_model_versions_model", "mlops_model_versions", ["model_id"])

    op.create_table(
        "mlops_experiments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "mlops_training_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("experiment_id", sa.String(36), nullable=False, index=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("model_id", sa.String(36), nullable=True, index=True),
        sa.Column("version_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="created"),
        sa.Column("hyperparameters_json", sa.JSON(), nullable=True),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )
    op.create_index("ix_mlops_training_runs_experiment", "mlops_training_runs", ["experiment_id"])

    op.create_table(
        "mlops_evaluations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_id", sa.String(36), nullable=False, index=True),
        sa.Column("version_id", sa.String(36), nullable=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("run_id", sa.String(36), nullable=True, index=True),
        sa.Column("dataset_name", sa.String(255), nullable=True),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="created"),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )
    op.create_index("ix_mlops_evaluations_model", "mlops_evaluations", ["model_id"])

    op.create_table(
        "mlops_deployments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_id", sa.String(36), nullable=False, index=True),
        sa.Column("version_id", sa.String(36), nullable=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("endpoint_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="created"),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deployed_at", sa.DateTime(), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_mlops_deployments_model", "mlops_deployments", ["model_id"])

    op.create_table(
        "mlops_monitoring",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("deployment_id", sa.String(36), nullable=False, index=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="created"),
        sa.Column("recorded_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_mlops_monitoring_deployment", "mlops_monitoring", ["deployment_id"])


def downgrade() -> None:
    op.drop_index("ix_mlops_monitoring_deployment", table_name="mlops_monitoring")
    op.drop_table("mlops_monitoring")
    op.drop_index("ix_mlops_deployments_model", table_name="mlops_deployments")
    op.drop_table("mlops_deployments")
    op.drop_index("ix_mlops_evaluations_model", table_name="mlops_evaluations")
    op.drop_table("mlops_evaluations")
    op.drop_index("ix_mlops_training_runs_experiment", table_name="mlops_training_runs")
    op.drop_table("mlops_training_runs")
    op.drop_table("mlops_experiments")
    op.drop_index("ix_mlops_model_versions_model", table_name="mlops_model_versions")
    op.drop_table("mlops_model_versions")
    op.drop_table("mlops_models")
