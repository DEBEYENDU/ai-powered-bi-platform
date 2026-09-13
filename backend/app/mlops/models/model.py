"""SQLAlchemy models for the MLOps lifecycle management system."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

try:
    from app.db.base import Base  # type: ignore
except ImportError:  # pragma: no cover
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):  # type: ignore[no-redef]
        pass


def _uuid() -> str:
    return str(uuid.uuid4())


# --- MLOps Model Registry ---


class MLOpsModel(Base):
    __tablename__ = "mlops_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    model_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    framework: Mapped[str] = mapped_column(String(50), default="sklearn")
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# --- Model Version ---


class MLOpsModelVersion(Base):
    __tablename__ = "mlops_model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(500), default="")
    checksum: Mapped[str] = mapped_column(String(128), default="")
    framework: Mapped[str] = mapped_column(String(50), default="")
    runtime_version: Mapped[str] = mapped_column(String(50), default="")
    training_dataset_id: Mapped[str] = mapped_column(String(255), default="")
    training_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    feature_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    hyperparameters: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    evaluation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="created")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str] = mapped_column(String(36), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# --- Experiment ---


class MLOpsExperiment(Base):
    __tablename__ = "mlops_experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    objective: Mapped[str] = mapped_column(String(500), default="")
    dataset_id: Mapped[str] = mapped_column(String(255), default="")
    model_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_by: Mapped[str] = mapped_column(String(36), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# --- Training Run ---


class MLOpsTrainingRun(Base):
    __tablename__ = "mlops_training_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    model_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(String(255), default="")
    target_column: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(50), default="queued")
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_path: Mapped[str] = mapped_column(String(500), default="")
    logs: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# --- Evaluation ---


class MLOpsEvaluation(Base):
    __tablename__ = "mlops_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_version_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(String(255), default="")
    dataset_name: Mapped[str] = mapped_column(String(255), default="")
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    metric_definitions: Mapped[dict] = mapped_column(JSON, default=dict)
    evaluation_type: Mapped[str] = mapped_column(String(50), default="test")
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    evaluator_version: Mapped[str] = mapped_column(String(50), default="1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# --- Deployment ---


class MLOpsDeployment(Base):
    __tablename__ = "mlops_deployments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    model_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="deploying")
    endpoint: Mapped[str] = mapped_column(String(500), default="")
    health_status: Mapped[str] = mapped_column(String(50), default="unknown")
    deployed_by: Mapped[str] = mapped_column(String(36), default="")
    deployed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    traffic_percentage: Mapped[float] = mapped_column(Float, default=100.0)


# --- Monitoring ---


class MLOpsMonitoringRecord(Base):
    __tablename__ = "mlops_monitoring"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    model_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, default=0.0)
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(50), default="normal")
    message: Mapped[str] = mapped_column(Text, default="")
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
