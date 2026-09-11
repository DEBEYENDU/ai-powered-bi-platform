"""SQLAlchemy models for the Multi-Agent platform."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

try:
    from app.db.base import Base
except ImportError:
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class AgentTaskRecord(Base):
    __tablename__ = "ai_agent_tasks"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    owner_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    task_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    agent_sequence: Mapped[list] = mapped_column(JSON, default=list)
    answer: Mapped[str] = mapped_column(Text, default="")
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    artifacts: Mapped[list] = mapped_column(JSON, default=list)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    session_id: Mapped[str] = mapped_column(String(100), default="")
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgentLogRecord(Base):
    __tablename__ = "ai_agent_logs"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    level: Mapped[str] = mapped_column(String(20), default="info", index=True)
    agent_type: Mapped[str] = mapped_column(String(50), default="", index=True)
    task_id: Mapped[str] = mapped_column(String(50), default="", index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class AgentMetricRecord(Base):
    __tablename__ = "ai_agent_metrics"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    calls: Mapped[int] = mapped_column(Integer, default=0)
    successes: Mapped[int] = mapped_column(Integer, default=0)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    avg_duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
