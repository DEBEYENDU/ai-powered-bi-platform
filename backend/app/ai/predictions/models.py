"""SQLAlchemy models for the AI Predictions platform."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

try:
    from app.db.base import Base  # type: ignore
except ImportError:  # pragma: no cover
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):  # type: ignore[no-redef]
        pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class PredictionModelRecord(Base):
    """Registered ML model with versioning."""

    __tablename__ = "ai_prediction_models"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    owner_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="training", index=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    hyperparameters: Mapped[dict] = mapped_column(JSON, default=dict)
    feature_names: Mapped[list] = mapped_column(JSON, default=list)
    feature_importances: Mapped[list] = mapped_column(JSON, default=list)
    model_path: Mapped[str] = mapped_column(String(500), default="")
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PredictionRecord(Base):
    """Stored prediction result."""

    __tablename__ = "ai_predictions"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    horizon: Mapped[str] = mapped_column(String(50), nullable=False)
    predictions: Mapped[list] = mapped_column(JSON, default=list)
    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    trend: Mapped[str] = mapped_column(String(50), default="stable")
    growth_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    explainability: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendations: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ModelVersionRecord(Base):
    """Immutable model version snapshot."""

    __tablename__ = "ai_model_versions"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    hyperparameters: Mapped[dict] = mapped_column(JSON, default=dict)
    model_path: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(50), default="ready")
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DriftRecord(Base):
    """Model/data drift monitoring records."""

    __tablename__ = "ai_prediction_drift"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    drift_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), default="low")
    feature: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    recommended_action: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScenarioRecord(Base):
    """What-if scenario results."""

    __tablename__ = "ai_scenarios"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    prediction_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_type: Mapped[str] = mapped_column(String(50), nullable=False)
    variables: Mapped[dict] = mapped_column(JSON, default=dict)
    predicted_impact: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
