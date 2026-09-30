"""Align remaining MLOps tables with the application models.

Revision ID: 0019
Revises: 0018
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # mlops_model_versions
    op.add_column("mlops_model_versions", sa.Column("version", sa.String(20), server_default="1", nullable=False))
    op.add_column("mlops_model_versions", sa.Column("checksum", sa.String(128), server_default="", nullable=False))
    op.add_column("mlops_model_versions", sa.Column("framework", sa.String(50), server_default="", nullable=False))
    op.add_column("mlops_model_versions", sa.Column("runtime_version", sa.String(50), server_default="", nullable=False))
    op.add_column("mlops_model_versions", sa.Column("training_dataset_id", sa.String(255), server_default="", nullable=False))
    op.add_column("mlops_model_versions", sa.Column("training_run_id", sa.String(36), nullable=True))
    op.add_column("mlops_model_versions", sa.Column("feature_schema", JSON, nullable=True))
    op.add_column("mlops_model_versions", sa.Column("hyperparameters", JSON, nullable=True))
    op.add_column("mlops_model_versions", sa.Column("metrics", JSON, nullable=True))
    op.add_column("mlops_model_versions", sa.Column("evaluation_id", sa.String(36), nullable=True))
    op.add_column("mlops_model_versions", sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False))

    # mlops_experiments
    op.add_column("mlops_experiments", sa.Column("objective", sa.String(500), server_default="", nullable=False))
    op.add_column("mlops_experiments", sa.Column("dataset_id", sa.String(255), server_default="", nullable=False))
    op.add_column("mlops_experiments", sa.Column("model_id", sa.String(36), nullable=True))
    op.add_column("mlops_experiments", sa.Column("status", sa.String(50), server_default="active", nullable=False))
    op.add_column("mlops_experiments", sa.Column("created_by", sa.String(36), server_default="", nullable=False))

    # mlops_training_runs
    op.add_column("mlops_training_runs", sa.Column("dataset_id", sa.String(255), server_default="", nullable=False))
    op.add_column("mlops_training_runs", sa.Column("target_column", sa.String(255), server_default="", nullable=False))
    op.add_column("mlops_training_runs", sa.Column("parameters", JSON, nullable=True))
    op.add_column("mlops_training_runs", sa.Column("metrics", JSON, nullable=True))
    op.add_column("mlops_training_runs", sa.Column("logs", sa.Text(), server_default="", nullable=False))
    op.add_column("mlops_training_runs", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column("mlops_training_runs", sa.Column("created_by", sa.String(36), server_default="", nullable=False))

    # mlops_evaluations
    op.add_column("mlops_evaluations", sa.Column("model_version_id", sa.String(36), server_default="", nullable=False))
    op.add_column("mlops_evaluations", sa.Column("dataset_id", sa.String(255), server_default="", nullable=False))
    op.add_column("mlops_evaluations", sa.Column("metrics", JSON, nullable=True))
    op.add_column("mlops_evaluations", sa.Column("metric_definitions", JSON, nullable=True))
    op.add_column("mlops_evaluations", sa.Column("evaluation_type", sa.String(50), server_default="test", nullable=False))
    op.add_column("mlops_evaluations", sa.Column("sample_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("mlops_evaluations", sa.Column("evaluator_version", sa.String(50), server_default="1.0", nullable=False))

    # mlops_deployments
    op.add_column("mlops_deployments", sa.Column("model_version_id", sa.String(36), server_default="", nullable=False))
    op.add_column("mlops_deployments", sa.Column("environment", sa.String(50), server_default="development", nullable=False))
    op.add_column("mlops_deployments", sa.Column("endpoint", sa.String(500), server_default="", nullable=False))
    op.add_column("mlops_deployments", sa.Column("health_status", sa.String(50), server_default="unknown", nullable=False))
    op.add_column("mlops_deployments", sa.Column("deployed_by", sa.String(36), server_default="", nullable=False))
    op.add_column("mlops_deployments", sa.Column("stopped_at", sa.DateTime(), nullable=True))
    op.add_column("mlops_deployments", sa.Column("config", JSON, nullable=True))
    op.add_column("mlops_deployments", sa.Column("traffic_percentage", sa.Float(), server_default="100.0", nullable=False))

    # mlops_monitoring
    op.add_column("mlops_monitoring", sa.Column("model_id", sa.String(36), server_default="", nullable=False))
    op.add_column("mlops_monitoring", sa.Column("model_version_id", sa.String(36), nullable=True))
    op.add_column("mlops_monitoring", sa.Column("metric_type", sa.String(50), server_default="metric", nullable=False))
    op.add_column("mlops_monitoring", sa.Column("dimensions", JSON, nullable=True))
    op.add_column("mlops_monitoring", sa.Column("message", sa.Text(), server_default="", nullable=False))


def downgrade() -> None:
    op.drop_column("mlops_monitoring", "message")
    op.drop_column("mlops_monitoring", "dimensions")
    op.drop_column("mlops_monitoring", "metric_type")
    op.drop_column("mlops_monitoring", "model_version_id")
    op.drop_column("mlops_monitoring", "model_id")
    op.drop_column("mlops_deployments", "traffic_percentage")
    op.drop_column("mlops_deployments", "config")
    op.drop_column("mlops_deployments", "stopped_at")
    op.drop_column("mlops_deployments", "deployed_by")
    op.drop_column("mlops_deployments", "health_status")
    op.drop_column("mlops_deployments", "endpoint")
    op.drop_column("mlops_deployments", "environment")
    op.drop_column("mlops_deployments", "model_version_id")
    op.drop_column("mlops_evaluations", "evaluator_version")
    op.drop_column("mlops_evaluations", "sample_count")
    op.drop_column("mlops_evaluations", "evaluation_type")
    op.drop_column("mlops_evaluations", "metric_definitions")
    op.drop_column("mlops_evaluations", "metrics")
    op.drop_column("mlops_evaluations", "dataset_id")
    op.drop_column("mlops_evaluations", "model_version_id")
    op.drop_column("mlops_training_runs", "created_by")
    op.drop_column("mlops_training_runs", "duration_ms")
    op.drop_column("mlops_training_runs", "logs")
    op.drop_column("mlops_training_runs", "metrics")
    op.drop_column("mlops_training_runs", "parameters")
    op.drop_column("mlops_training_runs", "target_column")
    op.drop_column("mlops_training_runs", "dataset_id")
    op.drop_column("mlops_experiments", "created_by")
    op.drop_column("mlops_experiments", "status")
    op.drop_column("mlops_experiments", "model_id")
    op.drop_column("mlops_experiments", "dataset_id")
    op.drop_column("mlops_experiments", "objective")
    op.drop_column("mlops_model_versions", "is_active")
    op.drop_column("mlops_model_versions", "evaluation_id")
    op.drop_column("mlops_model_versions", "metrics")
    op.drop_column("mlops_model_versions", "hyperparameters")
    op.drop_column("mlops_model_versions", "feature_schema")
    op.drop_column("mlops_model_versions", "training_run_id")
    op.drop_column("mlops_model_versions", "training_dataset_id")
    op.drop_column("mlops_model_versions", "runtime_version")
    op.drop_column("mlops_model_versions", "framework")
    op.drop_column("mlops_model_versions", "checksum")
    op.drop_column("mlops_model_versions", "version")
