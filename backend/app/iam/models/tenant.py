"""Tenant billing models — Plan, Subscription, UsageRecord, TenantApiKey, TenantConfiguration."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_users: Mapped[int] = mapped_column(Integer, default=3)
    max_datasets: Mapped[int] = mapped_column(Integer, default=5)
    max_storage_mb: Mapped[int] = mapped_column(Integer, default=100)
    max_ai_requests: Mapped[int] = mapped_column(Integer, default=50)
    max_ai_tokens: Mapped[int] = mapped_column(Integer, default=10000)
    max_workflows: Mapped[int] = mapped_column(Integer, default=2)
    max_reports: Mapped[int] = mapped_column(Integer, default=5)
    max_dashboards: Mapped[int] = mapped_column(Integer, default=5)
    max_rag_documents: Mapped[int] = mapped_column(Integer, default=20)
    max_rag_storage_mb: Mapped[int] = mapped_column(Integer, default=50)
    max_predictions: Mapped[int] = mapped_column(Integer, default=10)
    max_api_keys: Mapped[int] = mapped_column(Integer, default=2)
    max_queries_per_minute: Mapped[int] = mapped_column(Integer, default=30)
    max_concurrent_queries: Mapped[int] = mapped_column(Integer, default=2)
    price_monthly: Mapped[float | None] = mapped_column(nullable=True)
    price_yearly: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[str] = mapped_column(primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="trialing")
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    external_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UsageRecord(Base):
    __tablename__ = "usage_records"
    id: Mapped[str] = mapped_column(primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TenantApiKey(Base):
    __tablename__ = "tenant_api_keys"
    id: Mapped[str] = mapped_column(primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TenantConfiguration(Base):
    __tablename__ = "tenant_configurations"
    id: Mapped[str] = mapped_column(primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), unique=True, nullable=False)
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    locale: Mapped[str | None] = mapped_column(String(10), nullable=True)
    branding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_preferences_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    retention_days: Mapped[int] = mapped_column(Integer, default=365)
    custom_settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
