"""Align mlops_models with the application model: add model_type, task_type,
status, deleted_at (missing from 0015, required by the model registry).

Revision ID: 0018
Revises: 0017
"""
from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mlops_models",
        sa.Column("model_type", sa.String(50), server_default="regression", nullable=False),
    )
    op.add_column(
        "mlops_models",
        sa.Column("task_type", sa.String(50), server_default="regression", nullable=False),
    )
    op.add_column(
        "mlops_models",
        sa.Column("status", sa.String(50), server_default="draft", nullable=False),
    )
    op.add_column("mlops_models", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_mlops_models_model_type", "mlops_models", ["model_type"])
    op.create_index("ix_mlops_models_status", "mlops_models", ["status"])


def downgrade() -> None:
    op.drop_index("ix_mlops_models_status", table_name="mlops_models")
    op.drop_index("ix_mlops_models_model_type", table_name="mlops_models")
    op.drop_column("mlops_models", "deleted_at")
    op.drop_column("mlops_models", "status")
    op.drop_column("mlops_models", "task_type")
    op.drop_column("mlops_models", "model_type")
