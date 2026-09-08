"""PostgreSQL persistence adapter for the admin domain.

Design (SOLID: one adapter, services stay decoupled from SQLAlchemy):
- ``session_scope()`` yields a ``Session`` when the database is reachable,
  else ``None``. Availability is probed at most once per 30s so a down
  database never slows requests (fast-fail, then cached).
- Services write to BOTH stores: DB first (source of truth when available),
  memory mirror always (keeps mixed-mode coherent and tests green).
- Reads prefer DB when available, else memory.
- All datetimes serialized to ISO strings at the boundary.

Nothing here changes service APIs: callers keep working with plain dicts.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

_db_available: bool | None = None
_db_checked_at: float = 0.0
_AVAILABILITY_TTL = 30.0


def db_available() -> bool:
    """Cached reachability probe (fast-fail; never raises)."""
    global _db_available, _db_checked_at
    now = time.time()
    if _db_available is not None and now - _db_checked_at < _AVAILABILITY_TTL:
        return _db_available
    try:
        from sqlalchemy import text

        from app.db.session import get_engine

        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        _db_available = True
    except Exception:
        _db_available = False
    _db_checked_at = now
    return _db_available


@contextmanager
def session_scope() -> Iterator[Any | None]:
    """Yield a Session, or None when the database is unreachable.

    A failed body marks the database unavailable (fast-fail for subsequent
    calls) and re-raises: callers decide fallback via suppress/except.
    Exactly one yield per path — yielding twice is illegal and raises
    RuntimeError("generator didn't stop").
    """
    global _db_available, _db_checked_at
    if not db_available():
        yield None
        return
    try:
        from app.db.session import get_db_session

        with get_db_session() as session:
            yield session
    except Exception:
        _db_available = False
        _db_checked_at = time.time()
        raise


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _row_to_dict(row: Any, fields: list[str]) -> dict[str, Any]:
    return {f: _iso(getattr(row, f, None)) for f in fields}


USER_FIELDS = [
    "id",
    "email",
    "username",
    "password_hash",
    "full_name",
    "organization_id",
    "is_active",
    "is_verified",
    "suspended",
    "created_at",
    "updated_at",
    "last_login_at",
]
ORG_FIELDS = ["id", "name", "slug", "owner_id", "suspended", "created_at", "deleted_at"]


# -- users --
def user_upsert(data: dict[str, Any]) -> bool:
    """Insert or update the iam.users row. Returns True when persisted."""
    with session_scope() as session:
        if session is None:
            return False
        from app.iam.models.user import User

        row = session.get(User, data["id"])
        if row is None:
            row = User(id=data["id"])
            session.add(row)
        for field in USER_FIELDS:
            if field in data and field != "id":
                setattr(row, field, data[field])
        # Empty-string org ids would violate the organizations FK; the
        # column is nullable, so normalize to NULL (means "no org").
        if not getattr(row, "organization_id", None):
            row.organization_id = None
        if getattr(row, "updated_at", None) is not None or hasattr(User, "updated_at"):
            row.updated_at = datetime.utcnow()
        return True


def user_fetch(user_id: str) -> dict[str, Any] | None:
    with session_scope() as session:
        if session is None:
            return None
        from app.iam.models.user import User

        row = session.get(User, user_id)
        return _row_to_dict(row, USER_FIELDS) if row else None


def user_list_db(organization_id: str | None = None) -> list[dict[str, Any]] | None:
    with session_scope() as session:
        if session is None:
            return None
        from sqlalchemy import select

        from app.iam.models.user import User

        stmt = select(User)
        if organization_id:
            stmt = stmt.where(User.organization_id == organization_id)
        return [_row_to_dict(r, USER_FIELDS) for r in session.scalars(stmt).all()]


# -- orgs / quotas --
ORG_QUOTA_FIELDS = [
    "organization_id",
    "storage_mb",
    "dataset_limit",
    "ai_requests_per_day",
    "api_requests_per_minute",
    "suspended",
]


def org_upsert(data: dict[str, Any]) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.iam.models.user import Organization

        row = session.get(Organization, data["id"])
        if row is None:
            row = Organization(id=data["id"])
            session.add(row)
        for field in ORG_FIELDS:
            if field in data and field != "id" and hasattr(Organization, field):
                setattr(row, field, data[field])
        return True


def org_list_db() -> list[dict[str, Any]] | None:
    with session_scope() as session:
        if session is None:
            return None
        from sqlalchemy import select

        from app.iam.models.user import Organization

        rows = session.scalars(select(Organization)).all()
        return [_row_to_dict(r, ORG_FIELDS) for r in rows]


def quota_upsert(data: dict[str, Any]) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import OrganizationQuotaRecord

        row = session.get(OrganizationQuotaRecord, data["organization_id"])
        if row is None:
            row = OrganizationQuotaRecord(organization_id=data["organization_id"])
            session.add(row)
        for field in ORG_QUOTA_FIELDS:
            if field in data and field != "organization_id":
                setattr(row, field, data[field])
        return True


# -- sessions / keys / login history --
def session_insert(data: dict[str, Any]) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import UserSessionRecord

        session.add(
            UserSessionRecord(**{k: v for k, v in data.items() if hasattr(UserSessionRecord, k)})
        )
        return True


def session_revoke_db(session_id: str) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import UserSessionRecord

        row = session.get(UserSessionRecord, session_id)
        if row is None:
            return False
        row.revoked = True
        return True


def api_key_insert(data: dict[str, Any]) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import ApiKeyRecord

        session.add(ApiKeyRecord(**{k: v for k, v in data.items() if hasattr(ApiKeyRecord, k)}))
        return True


def api_key_revoke_db(key_id: str) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import ApiKeyRecord

        row = session.get(ApiKeyRecord, key_id)
        if row is None:
            return False
        row.revoked = True
        return True


def login_insert(data: dict[str, Any]) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import LoginHistoryRecord

        session.add(
            LoginHistoryRecord(**{k: v for k, v in data.items() if hasattr(LoginHistoryRecord, k)})
        )
        return True


def login_history_db(user_id: str | None = None, limit: int = 100) -> list[dict[str, Any]] | None:
    with session_scope() as session:
        if session is None:
            return None
        from sqlalchemy import desc, select

        from app.admin.models.admin import LoginHistoryRecord

        stmt = select(LoginHistoryRecord).order_by(desc(LoginHistoryRecord.created_at)).limit(limit)
        if user_id:
            stmt = stmt.where(LoginHistoryRecord.user_id == user_id)
        return [
            {
                "user_id": r.user_id,
                "success": r.success,
                "ip_address": r.ip_address,
                "at": _iso(r.created_at),
            }
            for r in session.scalars(stmt).all()
        ]


# -- rbac --
def role_upsert(role_id: str, data: dict[str, Any], permissions: list[str]) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import PermissionRecord, RolePermissionRecord, RoleRecord

        row = session.get(RoleRecord, role_id)
        if row is None:
            row = RoleRecord(id=role_id)
            session.add(row)
        row.name = data.get("name", row.name)
        row.description = data.get("description", "")
        row.organization_id = data.get("organization_id")
        row.system_role = data.get("system_role", False)
        for existing in list(session.query(RolePermissionRecord).filter_by(role_id=role_id).all()):
            session.delete(existing)
        session.flush()
        from sqlalchemy import select

        for code in permissions:
            perm = session.scalars(
                select(PermissionRecord).where(PermissionRecord.code == code)
            ).first()
            if perm is None:
                continue
            session.add(RolePermissionRecord(role_id=role_id, permission_id=perm.id))
        return True


def permission_ensure(code: str, group: str, description: str) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from sqlalchemy import select

        from app.admin.models.admin import PermissionRecord

        exists = session.scalars(
            select(PermissionRecord).where(PermissionRecord.code == code)
        ).first()
        if exists is None:
            session.add(PermissionRecord(code=code, group=group, description=description))
        return True


def role_delete_db(role_id: str) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import RolePermissionRecord, RoleRecord, UserRoleRecord

        row = session.get(RoleRecord, role_id)
        if row is None:
            return False
        session.query(RolePermissionRecord).filter_by(role_id=role_id).delete()
        session.query(UserRoleRecord).filter_by(role_id=role_id).delete()
        session.delete(row)
        return True


def user_role_grant(user_id: str, role_id: str, organization_id: str | None) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from sqlalchemy import select

        from app.admin.models.admin import UserRoleRecord

        exists = session.scalars(
            select(UserRoleRecord).where(
                UserRoleRecord.user_id == user_id, UserRoleRecord.role_id == role_id
            )
        ).first()
        if exists is None:
            session.add(
                UserRoleRecord(user_id=user_id, role_id=role_id, organization_id=organization_id)
            )
        return True


def user_role_revoke_db(user_id: str, role_id: str) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from sqlalchemy import select

        from app.admin.models.admin import UserRoleRecord

        row = session.scalars(
            select(UserRoleRecord).where(
                UserRoleRecord.user_id == user_id, UserRoleRecord.role_id == role_id
            )
        ).first()
        if row is None:
            return False
        session.delete(row)
        return True


# -- generic append-only / kv stores --
def audit_insert(entry: dict[str, Any]) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import AuditLogRecord

        session.add(
            AuditLogRecord(**{k: v for k, v in entry.items() if hasattr(AuditLogRecord, k)})
        )
        return True


def audit_query_db(
    action: str | None = None,
    actor_id: str | None = None,
    organization_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]] | None:
    with session_scope() as session:
        if session is None:
            return None
        from sqlalchemy import desc, select

        from app.admin.models.admin import AuditLogRecord

        stmt = select(AuditLogRecord).order_by(desc(AuditLogRecord.created_at))
        if action:
            stmt = stmt.where(AuditLogRecord.action == action)
        if actor_id:
            stmt = stmt.where(AuditLogRecord.actor_id == actor_id)
        if organization_id:
            stmt = stmt.where(AuditLogRecord.organization_id == organization_id)
        stmt = stmt.limit(limit).offset(offset)
        rows = session.scalars(stmt).all()
        return [
            {
                "id": r.id,
                "organization_id": r.organization_id,
                "actor_id": r.actor_id,
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "details": r.details or {},
                "prev_hash": r.prev_hash,
                "entry_hash": r.entry_hash,
                "created_at": _iso(r.created_at),
            }
            for r in rows
        ]


def flag_upsert(data: dict[str, Any]) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from sqlalchemy import select

        from app.admin.models.admin import FeatureFlagRecord

        row = session.scalars(
            select(FeatureFlagRecord).where(FeatureFlagRecord.key == data["key"])
        ).first()
        if row is None:
            row = FeatureFlagRecord(key=data["key"])
            session.add(row)
        for field in (
            "description",
            "flag_type",
            "default_value",
            "rules",
            "enabled",
            "version",
            "killed",
        ):
            if field in data:
                setattr(row, field, data[field])
        return True


def flag_delete_db(key: str) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from sqlalchemy import select

        from app.admin.models.admin import FeatureFlagRecord

        row = session.scalars(select(FeatureFlagRecord).where(FeatureFlagRecord.key == key)).first()
        if row is None:
            return False
        session.delete(row)
        return True


def setting_upsert(key: str, value: Any, updated_by: str = "") -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import SystemSettingRecord

        row = session.get(SystemSettingRecord, key)
        if row is None:
            row = SystemSettingRecord(key=key)
            session.add(row)
        row.value = {"value": value}
        row.updated_by = updated_by
        return True


def _as_datetime(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return value


def maintenance_save(data: dict[str, Any]) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import MaintenanceWindowRecord

        record = {k: v for k, v in data.items() if hasattr(MaintenanceWindowRecord, k)}
        record["starts_at"] = _as_datetime(record.get("starts_at"))
        record["ends_at"] = _as_datetime(record.get("ends_at"))
        session.add(MaintenanceWindowRecord(**record))
        return True


def maintenance_latest() -> dict[str, Any] | None:
    with session_scope() as session:
        if session is None:
            return None
        from sqlalchemy import desc, select

        from app.admin.models.admin import MaintenanceWindowRecord

        row = session.scalars(
            select(MaintenanceWindowRecord)
            .order_by(desc(MaintenanceWindowRecord.created_at))
            .limit(1)
        ).first()
        if row is None:
            return None
        return {
            "mode": row.mode,
            "message": row.message or "",
            "starts_at": _iso(row.starts_at),
            "ends_at": _iso(row.ends_at),
        }


def alert_rule_upsert(rule_id: str, data: dict[str, Any]) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import AlertRuleRecord

        row = session.get(AlertRuleRecord, rule_id)
        if row is None:
            row = AlertRuleRecord(id=rule_id)
            session.add(row)
        for field in (
            "name",
            "metric",
            "operator",
            "threshold",
            "window_seconds",
            "severity",
            "enabled",
        ):
            if field in data:
                setattr(row, field, data[field])
        return True


def alert_rule_delete_db(rule_id: str) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import AlertRuleRecord

        row = session.get(AlertRuleRecord, rule_id)
        if row is None:
            return False
        session.delete(row)
        return True


def incident_upsert(data: dict[str, Any]) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import AlertIncidentRecord

        row = session.get(AlertIncidentRecord, data["id"])
        if row is None:
            row = AlertIncidentRecord(id=data["id"])
            session.add(row)
        for field in ("rule_id", "metric", "observed_value", "severity", "status"):
            if field in data:
                setattr(row, field, data[field])
        return True


def entity_counts() -> dict[str, int] | None:
    """Live row counts for inventory widgets; None when DB is unreachable."""
    with session_scope() as session:
        if session is None:
            return None
        from sqlalchemy import func, select

        from app.dashboards.models import Dashboard
        from app.dataset.models.dataset import Dataset
        from app.etl.models.job import ETLJob
        from app.iam.models.user import Organization

        counts: dict[str, int] = {}
        counts["organizations"] = (
            session.scalar(select(func.count()).select_from(Organization)) or 0
        )
        counts["datasets"] = session.scalar(select(func.count()).select_from(Dataset)) or 0
        counts["dashboards"] = session.scalar(select(func.count()).select_from(Dashboard)) or 0
        counts["etl_jobs"] = session.scalar(select(func.count()).select_from(ETLJob)) or 0
        try:
            from app.reports.models.report import ReportRecord

            counts["reports"] = session.scalar(select(func.count()).select_from(ReportRecord)) or 0
        except Exception:
            counts["reports"] = 0
        return counts


def notification_upsert(data: dict[str, Any]) -> bool:
    with session_scope() as session:
        if session is None:
            return False
        from app.admin.models.admin import NotificationRecord

        row = session.get(NotificationRecord, data["id"])
        if row is None:
            row = NotificationRecord(id=data["id"])
            session.add(row)
        for field in ("user_id", "organization_id", "kind", "title", "body", "read"):
            if field in data:
                setattr(row, field, data[field])
        return True
