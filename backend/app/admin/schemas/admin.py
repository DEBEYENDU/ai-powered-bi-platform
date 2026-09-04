"""Pydantic schemas for platform administration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- users ---
class AdminUserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    full_name: str = ""
    organization_id: str = ""


class AdminUserOut(BaseModel):
    id: str
    email: str
    full_name: str = ""
    organization_id: str = ""
    is_active: bool = True
    is_verified: bool = False
    suspended: bool = False
    mfa_enabled: bool = False
    last_login_at: datetime | None = None


class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=8)
    force_change_on_login: bool = False


class ApiKeyCreate(BaseModel):
    name: str = ""


class ApiKeyOut(BaseModel):
    id: str
    name: str
    key_prefix: str
    revoked: bool
    created_at: datetime


# --- organizations ---
class OrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = ""


class OrgOut(BaseModel):
    id: str
    name: str
    slug: str
    suspended: bool = False


class QuotaUpdate(BaseModel):
    storage_mb: int | None = None
    dataset_limit: int | None = None
    ai_requests_per_day: int | None = None
    api_requests_per_minute: int | None = None


# --- rbac ---
class RoleCreate(BaseModel):
    name: str
    description: str = ""
    organization_id: str | None = None
    permission_codes: list[str] = Field(default_factory=list)


class PermissionCheck(BaseModel):
    user_id: str
    permission: str
    organization_id: str | None = None


# --- feature flags ---
class FlagCreate(BaseModel):
    key: str
    description: str = ""
    flag_type: str = "boolean"
    default_value: dict[str, Any] = Field(default_factory=dict)
    rules: list[dict[str, Any]] = Field(default_factory=list)


class FlagEvaluate(BaseModel):
    key: str
    user_id: str | None = None
    organization_id: str | None = None
    environment: str = "production"


# --- settings / maintenance ---
class SettingUpdate(BaseModel):
    value: dict[str, Any]


class MaintenanceUpdate(BaseModel):
    mode: str = Field("off", description="off, readonly, maintenance")
    message: str = ""
    starts_at: datetime | None = None
    ends_at: datetime | None = None


# --- health / metrics ---
class HealthStatus(BaseModel):
    service: str
    status: str
    latency_ms: float = 0.0
    detail: str = ""


class MetricPoint(BaseModel):
    name: str
    value: float
    labels: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# --- alerts ---
class AlertRuleCreate(BaseModel):
    name: str
    metric: str
    operator: str = ">"
    threshold: float = 0.0
    window_seconds: int = 300
    severity: str = "warning"


# --- audit ---
class AuditQuery(BaseModel):
    action: str | None = None
    actor_id: str | None = None
    organization_id: str | None = None
    limit: int = 50
    offset: int = 0


# --- notifications ---
class NotificationCreate(BaseModel):
    user_id: str
    organization_id: str | None = None
    kind: str = "info"
    title: str = ""
    body: str = ""
