"""SQLAlchemy models for platform administration.

Design notes:
- ``AdminAuditLog`` is append-only by convention: the repository exposes no
  update/delete, and ``verify_chain`` detects tampering via a hash chain
  (each entry hashes the previous entry's hash).
- RBAC tables (``Role``, ``Permission``, ``RolePermission``, ``UserRole``)
  complete the Phase 4 plan; ``User``/``Organization`` themselves live in IAM.
- Quotas/limits live on ``OrganizationQuota`` so IAM models stay untouched.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime

try:
    from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
    from sqlalchemy.orm import Mapped, mapped_column

    try:
        from app.db.base import Base  # type: ignore
    except ImportError:  # pragma: no cover
        from sqlalchemy.orm import DeclarativeBase

        class Base(DeclarativeBase):  # type: ignore[no-redef]
            pass

    _HAS_SQLALCHEMY = True
except ImportError:  # pragma: no cover - minimal envs without sqlalchemy
    _HAS_SQLALCHEMY = False
    Base = object  # type: ignore[assignment,misc]

    def mapped_column(*args: object, **kwargs: object) -> None:  # type: ignore[misc]
        return None

    class Mapped:  # type: ignore[no-redef]
        def __class_getitem__(cls, item: object) -> type:
            return cls

    class _DummyType:  # type: ignore[misc]
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __call__(self, *args: object, **kwargs: object) -> _DummyType:
            return _DummyType()

    JSON = Boolean = DateTime = Float = Integer = String = Text = _DummyType  # type: ignore[assignment]
    ForeignKey = _DummyType  # type: ignore[assignment]


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class AuditLogRecord(Base):
    """Immutable administrative/operational audit entry with hash chain."""

    __tablename__ = "admin_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(_uuid()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    actor_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), default="")
    resource_id: Mapped[str] = mapped_column(String(255), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    entry_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    @staticmethod
    def compute_hash(
        prev_hash: str, action: str, resource: str, details: dict, created_at: str
    ) -> str:
        payload = json.dumps(
            {
                "prev": prev_hash,
                "action": action,
                "resource": resource,
                "details": details,
                "at": created_at,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


class RoleRecord(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(_uuid()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    system_role: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PermissionRecord(Base):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(_uuid()))
    code: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    group: Mapped[str] = mapped_column(String(100), default="general")
    description: Mapped[str] = mapped_column(Text, default="")


class RolePermissionRecord(Base):
    __tablename__ = "role_permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(_uuid()))
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"), index=True)
    permission_id: Mapped[str] = mapped_column(String(36), ForeignKey("permissions.id"), index=True)


class UserRoleRecord(Base):
    __tablename__ = "user_roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(_uuid()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"), index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FeatureFlagRecord(Base):
    __tablename__ = "feature_flags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(_uuid()))
    key: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    flag_type: Mapped[str] = mapped_column(String(30), default="boolean")
    default_value: Mapped[dict] = mapped_column(JSON, default=dict)
    rules: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class SystemSettingRecord(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(150), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_by: Mapped[str] = mapped_column(String(255), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AlertRuleRecord(Base):
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(_uuid()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    operator: Mapped[str] = mapped_column(String(10), default=">")
    threshold: Mapped[float] = mapped_column(Float, default=0.0)
    window_seconds: Mapped[int] = mapped_column(Integer, default=300)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertIncidentRecord(Base):
    __tablename__ = "alert_incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(_uuid()))
    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("alert_rules.id"), index=True)
    metric: Mapped[str] = mapped_column(String(150), default="")
    observed_value: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    status: Mapped[str] = mapped_column(String(20), default="firing")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ApiKeyRecord(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(_uuid()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserSessionRecord(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(_uuid()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(512), default="")
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OrganizationQuotaRecord(Base):
    __tablename__ = "organization_quotas"

    organization_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    storage_mb: Mapped[int] = mapped_column(Integer, default=10240)
    dataset_limit: Mapped[int] = mapped_column(Integer, default=100)
    ai_requests_per_day: Mapped[int] = mapped_column(Integer, default=1000)
    api_requests_per_minute: Mapped[int] = mapped_column(Integer, default=120)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class MaintenanceWindowRecord(Base):
    __tablename__ = "maintenance_windows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(_uuid()))
    mode: Mapped[str] = mapped_column(String(30), default="off")
    message: Mapped[str] = mapped_column(Text, default="")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationRecord(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(_uuid()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(50), default="info")
    title: Mapped[str] = mapped_column(String(255), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class SystemRoles:
    SUPERADMIN = "superadmin"
    ORG_ADMIN = "org_admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


DEFAULT_PERMISSIONS = [
    ("users:read", "users", "View users"),
    ("users:write", "users", "Create/update users"),
    ("users:suspend", "users", "Suspend/unsuspend users"),
    ("orgs:read", "organizations", "View organizations"),
    ("orgs:write", "organizations", "Create/update organizations"),
    ("orgs:suspend", "organizations", "Suspend organizations"),
    ("roles:manage", "rbac", "Manage roles and permissions"),
    ("datasets:read", "data", "View datasets"),
    ("datasets:write", "data", "Upload/modify datasets"),
    ("etl:run", "data", "Run ETL jobs"),
    ("analytics:read", "analytics", "View analytics"),
    ("dashboards:read", "dashboards", "View dashboards"),
    ("dashboards:write", "dashboards", "Edit dashboards"),
    ("reports:read", "reports", "View reports"),
    ("reports:write", "reports", "Create reports"),
    ("ai:use", "ai", "Use AI assistant"),
    ("ml:use", "ml", "Use ML models"),
    ("admin:settings", "admin", "Change system settings"),
    ("admin:flags", "admin", "Manage feature flags"),
    ("admin:alerts", "admin", "Manage alerts"),
]
