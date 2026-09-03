"""SQLAlchemy models for the Reporting Engine.

Reuses the same conventions as existing modules (UUID PKs, audit fields,
soft deletes). These models are intentionally decoupled from analytics/AI
tables: reports reference datasets/dashboards by UUID instead of FK joins,
so the reporting layer never duplicates analytics logic.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

try:
    from app.db.base import Base  # type: ignore
except Exception:  # pragma: no cover - allows unit tests without db infra
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):  # type: ignore[no-redef]
        pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class ReportType(str, enum.Enum):
    EXECUTIVE = "executive"
    SALES = "sales"
    FINANCIAL = "financial"
    INVENTORY = "inventory"
    CUSTOMER = "customer"
    MARKETING = "marketing"
    OPERATIONS = "operations"
    FORECAST = "forecast"
    PERFORMANCE = "performance"
    AUDIT = "audit"
    COMPLIANCE = "compliance"
    CUSTOM = "custom"


class ReportStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    FAILED = "failed"


class ScheduleFrequency(str, enum.Enum):
    ONE_TIME = "one_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CRON = "cron"


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    PAUSED = "paused"


class Report(Mapped if False else object):
    """Report metadata record (see module docstring for design notes)."""


class ReportRecord(Base):
    """Persistent report metadata."""

    __tablename__ = "reports"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    owner_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType), default=ReportType.CUSTOM, index=True)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.DRAFT, index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    dashboard_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    definition: Mapped[dict] = mapped_column(JSON, default=dict)  # sections, filters, variables
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ReportVersionRecord(Base):
    """Immutable snapshot of a published report version."""

    __tablename__ = "report_versions"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    report_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    rendered_formats: Mapped[list] = mapped_column(JSON, default=list)
    storage_paths: Mapped[dict] = mapped_column(JSON, default=dict)
    checksum_sha256: Mapped[str] = mapped_column(String(64), default="")
    approved_by: Mapped[str] = mapped_column(String(255), default="")
    change_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReportTemplateRecord(Base):
    """Reusable report template with versioning and approval."""

    __tablename__ = "report_templates"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    layout: Mapped[dict] = mapped_column(JSON, default=dict)  # branding, margins, orientation
    sections: Mapped[list] = mapped_column(JSON, default=list)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    shared: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ReportScheduleRecord(Base):
    """Scheduled report configuration."""

    __tablename__ = "report_schedules"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    report_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False, index=True
    )
    organization_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    frequency: Mapped[ScheduleFrequency] = mapped_column(Enum(ScheduleFrequency), default=ScheduleFrequency.DAILY)
    cron_expression: Mapped[str] = mapped_column(String(100), default="")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    distribution: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReportDeliveryRecord(Base):
    """Delivery attempt tracking."""

    __tablename__ = "report_deliveries"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    report_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    channel: Mapped[str] = mapped_column(String(50), default="download")  # email, download, link, webhook
    recipient: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[DeliveryStatus] = mapped_column(Enum(DeliveryStatus), default=DeliveryStatus.PENDING)
    error_message: Mapped[str] = mapped_column(Text, default="")
    execution_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReportShareRecord(Base):
    """Sharing / permission grant for a report."""

    __tablename__ = "report_shares"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    report_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False, index=True
    )
    granted_to: Mapped[str] = mapped_column(String(255), nullable=False)  # user id, role, dept, or 'org'
    role: Mapped[str] = mapped_column(String(50), default="viewer")  # owner/editor/reviewer/viewer
    can_export: Mapped[bool] = mapped_column(Boolean, default=True)
    can_distribute: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
