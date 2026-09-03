"""FastAPI routers for platform administration (/admin)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.admin.schemas.admin import (
    AdminUserCreate,
    AlertRuleCreate,
    ApiKeyCreate,
    FlagCreate,
    FlagEvaluate,
    MaintenanceUpdate,
    NotificationCreate,
    OrgCreate,
    PasswordReset,
    PermissionCheck,
    QuotaUpdate,
    RoleCreate,
    SettingUpdate,
)
from app.admin.services.platform import PlatformAdmin, get_platform

admin_router = APIRouter(prefix="/admin", tags=["Admin"])


def _not_found(value: Any, name: str) -> Any:
    if value is None:
        raise HTTPException(404, f"{name} not found")
    return value


# -- dashboard / status --
@admin_router.get("/overview", summary="Platform overview")
def overview(platform: PlatformAdmin = Depends(get_platform)):
    return platform.overview()


@admin_router.get("/status", summary="Platform status")
def status(platform: PlatformAdmin = Depends(get_platform)):
    return {"health": platform.health.check_all(),
            "maintenance": platform.settings.maintenance_status(),
            "system": platform.metrics.system_snapshot()}


# -- users --
@admin_router.post("/users", summary="Create user")
def create_user(payload: AdminUserCreate = Body(...),
                platform: PlatformAdmin = Depends(get_platform)):
    try:
        user = platform.users.create(payload.email, payload.password,
                                     payload.full_name, payload.organization_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    platform.audit.append("user_created", "user", user["id"], details={"email": user["email"]})
    return user


@admin_router.get("/users", summary="List users")
def list_users(organization_id: Optional[str] = Query(None),
               platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.users.list(organization_id)}


@admin_router.get("/users/{user_id}", summary="Get user")
def get_user(user_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.users.get(user_id), "User")


@admin_router.patch("/users/{user_id}", summary="Update user")
def update_user(user_id: str, patch: Dict[str, Any] = Body(...),
                platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.users.update(user_id, patch), "User")


@admin_router.post("/users/{user_id}/suspend", summary="Suspend user")
def suspend_user(user_id: str, platform: PlatformAdmin = Depends(get_platform)):
    user = _not_found(platform.users.suspend(user_id, True), "User")
    platform.audit.append("user_suspended", "user", user_id)
    return user


@admin_router.post("/users/{user_id}/unsuspend", summary="Unsuspend user")
def unsuspend_user(user_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.users.suspend(user_id, False), "User")


@admin_router.delete("/users/{user_id}", summary="Deactivate user")
def delete_user(user_id: str, platform: PlatformAdmin = Depends(get_platform)):
    if not platform.users.delete(user_id):
        raise HTTPException(404, "User not found")
    return {"deactivated": True}


@admin_router.post("/users/{user_id}/restore", summary="Restore user")
def restore_user(user_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.users.restore(user_id), "User")


@admin_router.post("/users/{user_id}/reset-password", summary="Reset password")
def reset_password(user_id: str, payload: PasswordReset = Body(...),
                   platform: PlatformAdmin = Depends(get_platform)):
    if not platform.users.reset_password(user_id, payload.new_password,
                                         payload.force_change_on_login):
        raise HTTPException(404, "User not found")
    platform.audit.append("password_reset", "user", user_id)
    return {"reset": True}


@admin_router.get("/users/{user_id}/sessions", summary="List sessions")
def list_sessions(user_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.users.sessions(user_id)}


@admin_router.delete("/sessions/{session_id}", summary="Revoke session")
def revoke_session(session_id: str, platform: PlatformAdmin = Depends(get_platform)):
    if not platform.users.revoke_session(session_id):
        raise HTTPException(404, "Session not found")
    return {"revoked": True}


@admin_router.get("/users/{user_id}/activity", summary="Login history")
def login_history(user_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.users.login_history(user_id)}


@admin_router.post("/users/{user_id}/api-keys", summary="Create API key")
def create_api_key(user_id: str, payload: ApiKeyCreate = Body(...),
                   platform: PlatformAdmin = Depends(get_platform)):
    return platform.users.create_api_key(user_id, payload.name)


@admin_router.delete("/api-keys/{key_id}", summary="Revoke API key")
def revoke_api_key(key_id: str, platform: PlatformAdmin = Depends(get_platform)):
    if not platform.users.revoke_api_key(key_id):
        raise HTTPException(404, "API key not found")
    return {"revoked": True}


# -- organizations --
@admin_router.post("/organizations", summary="Create organization")
def create_org(payload: OrgCreate = Body(...),
               platform: PlatformAdmin = Depends(get_platform)):
    try:
        return platform.orgs.create(payload.name, payload.slug)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@admin_router.get("/organizations", summary="List organizations")
def list_orgs(platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.orgs.list()}


@admin_router.get("/organizations/{org_id}", summary="Get organization")
def get_org(org_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.orgs.get(org_id), "Organization")


@admin_router.patch("/organizations/{org_id}", summary="Update organization")
def update_org(org_id: str, patch: Dict[str, Any] = Body(...),
               platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.orgs.update(org_id, patch), "Organization")


@admin_router.post("/organizations/{org_id}/suspend", summary="Suspend organization")
def suspend_org(org_id: str, platform: PlatformAdmin = Depends(get_platform)):
    org = _not_found(platform.orgs.suspend(org_id, True), "Organization")
    platform.audit.append("org_suspended", "organization", org_id)
    return org


@admin_router.post("/organizations/{org_id}/restore", summary="Restore organization")
def restore_org(org_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.orgs.restore(org_id), "Organization")


@admin_router.get("/organizations/{org_id}/quotas", summary="Get quotas")
def get_quotas(org_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.orgs.quotas(org_id), "Organization")


@admin_router.patch("/organizations/{org_id}/quotas", summary="Update quotas")
def update_quotas(org_id: str, payload: QuotaUpdate = Body(...),
                  platform: PlatformAdmin = Depends(get_platform)):
    try:
        return _not_found(platform.orgs.update_quotas(
            org_id, payload.dict(exclude_none=True)), "Organization")
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@admin_router.get("/organizations/{org_id}/settings", summary="Org settings")
def org_settings(org_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return platform.orgs.org_settings(org_id)


# -- rbac --
@admin_router.post("/roles", summary="Create role")
def create_role(payload: RoleCreate = Body(...),
                platform: PlatformAdmin = Depends(get_platform)):
    try:
        return platform.rbac.create_role(payload.name, payload.description,
                                         payload.organization_id,
                                         payload.permission_codes)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@admin_router.get("/roles", summary="List roles")
def list_roles(platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.rbac.list_roles()}


@admin_router.get("/permissions", summary="List permissions by group")
def list_permissions(platform: PlatformAdmin = Depends(get_platform)):
    return platform.rbac.permission_groups()


@admin_router.post("/users/{user_id}/roles/{role_id}", summary="Assign role")
def assign_role(user_id: str, role_id: str,
                platform: PlatformAdmin = Depends(get_platform)):
    try:
        platform.rbac.assign_role(user_id, role_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    platform.audit.append("role_assigned", "role", role_id,
                          details={"user_id": user_id})
    return {"assigned": True}


@admin_router.delete("/users/{user_id}/roles/{role_id}", summary="Unassign role")
def unassign_role(user_id: str, role_id: str,
                  platform: PlatformAdmin = Depends(get_platform)):
    return {"unassigned": platform.rbac.unassign_role(user_id, role_id)}


@admin_router.post("/permissions/check", summary="Check permission")
def check_permission(payload: PermissionCheck = Body(...),
                     platform: PlatformAdmin = Depends(get_platform)):
    return {"user_id": payload.user_id, "permission": payload.permission,
            "allowed": platform.rbac.check(payload.user_id, payload.permission)}


@admin_router.get("/users/{user_id}/permissions/simulate", summary="Permission simulator")
def simulate(user_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return platform.rbac.simulate(user_id)


# -- feature flags --
@admin_router.post("/flags", summary="Create flag")
def create_flag(payload: FlagCreate = Body(...),
                platform: PlatformAdmin = Depends(get_platform)):
    try:
        return platform.flags.create(payload.key, payload.description,
                                     payload.flag_type, payload.default_value,
                                     payload.rules)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@admin_router.get("/flags", summary="List flags")
def list_flags(platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.flags.list()}


@admin_router.post("/flags/evaluate", summary="Evaluate flag")
def evaluate_flag(payload: FlagEvaluate = Body(...),
                  platform: PlatformAdmin = Depends(get_platform)):
    try:
        return platform.flags.evaluate(payload.key, payload.user_id,
                                       payload.organization_id, payload.environment)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@admin_router.patch("/flags/{key}", summary="Update flag")
def update_flag(key: str, patch: Dict[str, Any] = Body(...),
                platform: PlatformAdmin = Depends(get_platform)):
    try:
        return platform.flags.update(key, patch)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@admin_router.post("/flags/{key}/kill", summary="Kill switch")
def kill_flag(key: str, platform: PlatformAdmin = Depends(get_platform)):
    try:
        flag = platform.flags.kill(key)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    platform.audit.append("flag_killed", "flag", key)
    return flag


@admin_router.get("/flags/history", summary="Flag history")
def flag_history(key: Optional[str] = Query(None),
                 platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.flags.history(key)}


# -- settings / maintenance --
@admin_router.get("/settings", summary="All settings")
def all_settings(platform: PlatformAdmin = Depends(get_platform)):
    return platform.settings.all()


@admin_router.patch("/settings/{key}", summary="Update setting")
def update_setting(key: str, payload: SettingUpdate = Body(...),
                   platform: PlatformAdmin = Depends(get_platform)):
    try:
        value = platform.settings.update(key, payload.value.get("value"))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    platform.audit.append("setting_changed", "setting", key,
                          details={"value": value})
    return {"key": key, "value": value}


@admin_router.get("/maintenance", summary="Maintenance status")
def maintenance_status(platform: PlatformAdmin = Depends(get_platform)):
    return platform.settings.maintenance_status()


@admin_router.post("/maintenance", summary="Set maintenance mode")
def set_maintenance(payload: MaintenanceUpdate = Body(...),
                    platform: PlatformAdmin = Depends(get_platform)):
    try:
        return platform.settings.set_maintenance(
            payload.mode, payload.message, payload.starts_at, payload.ends_at)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@admin_router.post("/maintenance/override-token", summary="Mint admin override")
def mint_override(platform: PlatformAdmin = Depends(get_platform)):
    return {"token": platform.settings.mint_override_token("admin")}


# -- health / metrics / tracing --
@admin_router.get("/health", summary="Aggregate health")
def health(platform: PlatformAdmin = Depends(get_platform)):
    return platform.health.check_all()


@admin_router.get("/metrics", summary="System snapshot")
def metrics_snapshot(platform: PlatformAdmin = Depends(get_platform)):
    return platform.metrics.system_snapshot()


@admin_router.get("/metrics/platform", summary="Cross-module snapshot")
def platform_snapshot(platform: PlatformAdmin = Depends(get_platform)):
    return platform.metrics.platform_snapshot()


@admin_router.get("/metrics/prometheus", summary="Prometheus exposition",
                  response_class=PlainTextResponse)
def prometheus(platform: PlatformAdmin = Depends(get_platform)):
    return platform.metrics.render_prometheus()


@admin_router.post("/metrics/record", summary="Record metric")
def record_metric(name: str = Body(...), value: float = Body(...),
                  labels: Optional[Dict[str, str]] = Body(None),
                  platform: PlatformAdmin = Depends(get_platform)):
    platform.metrics.record(name, value, labels)
    return {"recorded": True}


@admin_router.get("/traces", summary="Recent traces")
def recent_traces(limit: int = Query(50, ge=1, le=500),
                  platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.tracer.recent(limit)}


@admin_router.get("/traces/{trace_id}", summary="Trace detail")
def trace_detail(trace_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.tracer.spans_for_trace(trace_id)}


# -- audit --
@admin_router.get("/audit", summary="Query audit log")
def query_audit(action: Optional[str] = Query(None),
                actor_id: Optional[str] = Query(None),
                organization_id: Optional[str] = Query(None),
                limit: int = Query(50, ge=1, le=500),
                offset: int = Query(0, ge=0),
                platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.audit.query(action, actor_id, organization_id,
                                         limit, offset)}


@admin_router.get("/audit/verify", summary="Verify audit chain")
def verify_audit(platform: PlatformAdmin = Depends(get_platform)):
    return platform.audit.verify_chain()


# -- alerts --
@admin_router.post("/alerts/rules", summary="Create alert rule")
def create_rule(payload: AlertRuleCreate = Body(...),
                platform: PlatformAdmin = Depends(get_platform)):
    try:
        return platform.alerts.create_rule(payload.name, payload.metric,
                                           payload.threshold, payload.operator,
                                           payload.window_seconds, payload.severity)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@admin_router.get("/alerts/rules", summary="List alert rules")
def list_rules(platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.alerts.list_rules()}


@admin_router.delete("/alerts/rules/{rule_id}", summary="Delete rule")
def delete_rule(rule_id: str, platform: PlatformAdmin = Depends(get_platform)):
    if not platform.alerts.delete_rule(rule_id):
        raise HTTPException(404, "Rule not found")
    return {"deleted": True}


@admin_router.get("/alerts/incidents", summary="List incidents")
def list_incidents(status: Optional[str] = Query(None),
                   platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.alerts.incidents(status)}


@admin_router.post("/alerts/incidents/{incident_id}/ack", summary="Acknowledge")
def acknowledge(incident_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.alerts.acknowledge(incident_id), "Incident")


@admin_router.post("/alerts/evaluate", summary="Evaluate metric")
def evaluate_alert(metric: str = Body(...), value: float = Body(...),
                   platform: PlatformAdmin = Depends(get_platform)):
    platform.metrics.record(metric, value)
    return {"fired": platform.alerts.evaluate(metric, value)}


# -- jobs / scheduler --
@admin_router.get("/jobs", summary="Job monitoring")
def job_status(platform: PlatformAdmin = Depends(get_platform)):
    return platform.jobs.status()


@admin_router.get("/jobs/queues", summary="Queue depths")
def job_queues(platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.jobs.queues()}


@admin_router.get("/scheduler", summary="Scheduler status")
def scheduler_status(platform: PlatformAdmin = Depends(get_platform)):
    try:
        from app.reports.services.report_service import ReportService  # type: ignore

        due = ReportService().scheduler.due_schedules()
        return {"due_count": len(due)}
    except Exception as exc:
        return {"due_count": 0, "detail": str(exc)[:200]}


# -- notifications --
@admin_router.post("/notifications", summary="Create notification")
def create_notification(payload: NotificationCreate = Body(...),
                        platform: PlatformAdmin = Depends(get_platform)):
    return platform.notifications.create(payload.user_id, payload.title,
                                         payload.body, payload.kind,
                                         payload.organization_id)


@admin_router.get("/notifications", summary="List notifications")
def list_notifications(user_id: Optional[str] = Query(None),
                       unread_only: bool = Query(False),
                       platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.notifications.list(user_id, unread_only)}


@admin_router.post("/notifications/{notification_id}/read", summary="Mark read")
def mark_read(notification_id: str,
              platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.notifications.mark_read(notification_id),
                      "Notification")
