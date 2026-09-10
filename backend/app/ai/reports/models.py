"""SQLAlchemy model for AI-generated reports."""

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


class AIReportRecord(Base):
    """AI-generated report with full content and metadata."""

    __tablename__ = "ai_reports"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    owner_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), default="custom", index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    dashboard_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    executive_summary: Mapped[str] = mapped_column(Text, default="")
    sections: Mapped[list] = mapped_column(JSON, default=list)
    kpis: Mapped[list] = mapped_column(JSON, default=list)
    charts: Mapped[list] = mapped_column(JSON, default=list)
    insights: Mapped[list] = mapped_column(JSON, default=list)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    recommendations: Mapped[list] = mapped_column(JSON, default=list)
    branding: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    generation_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AIReportVersionRecord(Base):
    """Immutable snapshot of an AI report version."""

    __tablename__ = "ai_report_versions"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    report_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    formats_generated: Mapped[list] = mapped_column(JSON, default=list)
    storage_paths: Mapped[dict] = mapped_column(JSON, default=dict)
    change_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
