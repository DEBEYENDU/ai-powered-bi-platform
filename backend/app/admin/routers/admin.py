"""FastAPI routers for platform administration (/admin)."""

from __future__ import annotations

import contextlib
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response

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
    return {
        "health": platform.health.check_all(),
        "maintenance": platform.settings.maintenance_status(),
        "system": platform.metrics.system_snapshot(),
    }


# -- users --
@admin_router.post("/users", summary="Create user")
def create_user(
    payload: AdminUserCreate = Body(...), platform: PlatformAdmin = Depends(get_platform)
):
    if payload.organization_id:
        org = platform.orgs.get(payload.organization_id)
        if org is None:
            raise HTTPException(400, "Organization not found")
    try:
        user = platform.users.create(
            payload.email,
            payload.password,
            payload.full_name,
            payload.organization_id,
            payload.username,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    for role_id in payload.role_ids:
        with contextlib.suppress(ValueError):
            platform.rbac.assign_role(user["id"], role_id)
    platform.audit.append("user_created", "user", user["id"], details={"email": user["email"]})
    return user


@admin_router.get("/users", summary="List users")
def list_users(
    organization_id: str | None = Query(None), platform: PlatformAdmin = Depends(get_platform)
):
    users = platform.users.list(organization_id)
    for user in users:
        user["roles"] = [r["name"] for r in platform.rbac.user_roles(user["id"])]
    return {"data": users}


@admin_router.get("/users/{user_id}", summary="Get user")
def get_user(user_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.users.get(user_id), "User")


@admin_router.patch("/users/{user_id}", summary="Update user")
def update_user(
    user_id: str, patch: dict[str, Any] = Body(...), platform: PlatformAdmin = Depends(get_platform)
):
    _not_found(platform.users.get(user_id), "User")
    if patch.get("organization_id"):
        org = platform.orgs.get(patch["organization_id"])
        if org is None:
            raise HTTPException(400, "Organization not found")
    try:
        return _not_found(platform.users.update(user_id, patch), "User")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


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
def reset_password(
    user_id: str,
    payload: PasswordReset = Body(...),
    platform: PlatformAdmin = Depends(get_platform),
):
    if not platform.users.reset_password(
        user_id, payload.new_password, payload.force_change_on_login
    ):
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
def create_api_key(
    user_id: str, payload: ApiKeyCreate = Body(...), platform: PlatformAdmin = Depends(get_platform)
):
    return platform.users.create_api_key(user_id, payload.name)


@admin_router.delete("/api-keys/{key_id}", summary="Revoke API key")
def revoke_api_key(key_id: str, platform: PlatformAdmin = Depends(get_platform)):
    if not platform.users.revoke_api_key(key_id):
        raise HTTPException(404, "API key not found")
    return {"revoked": True}


# -- organizations --
@admin_router.post("/organizations", summary="Create organization")
def create_org(payload: OrgCreate = Body(...), platform: PlatformAdmin = Depends(get_platform)):
    if payload.owner_id:
        owner = platform.users.get(payload.owner_id)
        if owner is None:
            raise HTTPException(400, "Owner user not found")
    try:
        org = platform.orgs.create(payload.name, payload.slug, payload.owner_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    platform.audit.append("org_created", "organization", org["id"], details={"name": org["name"]})
    return org


@admin_router.get("/organizations", summary="List organizations")
def list_orgs(platform: PlatformAdmin = Depends(get_platform)):
    orgs = platform.orgs.list(include_archived=True)
    counts: dict[str, int] = {}
    for user in platform.users.list(include_inactive=True):
        oid = user.get("organization_id") or ""
        counts[oid] = counts.get(oid, 0) + 1
    for org in orgs:
        org["user_count"] = counts.get(org["id"], 0)
    return {"data": orgs}


@admin_router.get("/organizations/{org_id}", summary="Get organization")
def get_org(org_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.orgs.get(org_id), "Organization")


@admin_router.patch("/organizations/{org_id}", summary="Update organization")
def update_org(
    org_id: str, patch: dict[str, Any] = Body(...), platform: PlatformAdmin = Depends(get_platform)
):
    _not_found(platform.orgs.get(org_id), "Organization")
    if patch.get("owner_id"):
        owner = platform.users.get(patch["owner_id"])
        if owner is None:
            raise HTTPException(400, "Owner user not found")
    if patch.get("slug"):
        existing = platform.orgs._merged()
        for o in existing.values():
            if o["slug"] == patch["slug"] and o["id"] != org_id:
                raise HTTPException(400, f"Organization with slug '{patch['slug']}' already exists")
    return _not_found(platform.orgs.update(org_id, patch), "Organization")


@admin_router.post("/organizations/{org_id}/suspend", summary="Suspend organization")
def suspend_org(org_id: str, platform: PlatformAdmin = Depends(get_platform)):
    org = _not_found(platform.orgs.suspend(org_id, True), "Organization")
    platform.audit.append("org_suspended", "organization", org_id)
    return org


@admin_router.post("/organizations/{org_id}/restore", summary="Restore organization")
def restore_org(org_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.orgs.restore(org_id), "Organization")


@admin_router.delete("/organizations/{org_id}", summary="Delete organization")
def delete_org(org_id: str, platform: PlatformAdmin = Depends(get_platform)):
    if not platform.orgs.delete(org_id):
        raise HTTPException(404, "Organization not found")
    platform.audit.append("org_deleted", "organization", org_id)
    return {"deleted": True}


@admin_router.get("/organizations/{org_id}/quotas", summary="Get quotas")
def get_quotas(org_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.orgs.quotas(org_id), "Organization")


@admin_router.patch("/organizations/{org_id}/quotas", summary="Update quotas")
def update_quotas(
    org_id: str, payload: QuotaUpdate = Body(...), platform: PlatformAdmin = Depends(get_platform)
):
    try:
        return _not_found(
            platform.orgs.update_quotas(org_id, payload.dict(exclude_none=True)), "Organization"
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@admin_router.get("/organizations/{org_id}/settings", summary="Org settings")
def org_settings(org_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return platform.orgs.org_settings(org_id)


# -- rbac --
@admin_router.post("/roles", summary="Create role")
def create_role(payload: RoleCreate = Body(...), platform: PlatformAdmin = Depends(get_platform)):
    try:
        return platform.rbac.create_role(
            payload.name, payload.description, payload.organization_id, payload.permission_codes
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@admin_router.delete("/roles/{role_id}", summary="Delete role")
def delete_role(role_id: str, platform: PlatformAdmin = Depends(get_platform)):
    try:
        if not platform.rbac.delete_role(role_id):
            raise HTTPException(404, "Role not found")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    platform.audit.append("role_deleted", "role", role_id)
    return {"deleted": True}


@admin_router.get("/roles/{role_id}", summary="Get role with grants")
def get_role(role_id: str, platform: PlatformAdmin = Depends(get_platform)):
    role = platform.rbac.get_role(role_id)
    if role is None:
        raise HTTPException(404, "Role not found")
    return role


@admin_router.get("/roles", summary="List roles")
def list_roles(platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.rbac.list_roles()}


@admin_router.get("/permissions", summary="List permissions by group")
def list_permissions(platform: PlatformAdmin = Depends(get_platform)):
    return platform.rbac.permission_groups()


@admin_router.post("/users/{user_id}/roles/{role_id}", summary="Assign role")
def assign_role(user_id: str, role_id: str, platform: PlatformAdmin = Depends(get_platform)):
    try:
        platform.rbac.assign_role(user_id, role_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    platform.audit.append("role_assigned", "role", role_id, details={"user_id": user_id})
    return {"assigned": True}


@admin_router.delete("/users/{user_id}/roles/{role_id}", summary="Unassign role")
def unassign_role(user_id: str, role_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return {"unassigned": platform.rbac.unassign_role(user_id, role_id)}


@admin_router.post("/permissions/check", summary="Check permission")
def check_permission(
    payload: PermissionCheck = Body(...), platform: PlatformAdmin = Depends(get_platform)
):
    return {
        "user_id": payload.user_id,
        "permission": payload.permission,
        "allowed": platform.rbac.check(payload.user_id, payload.permission),
    }


@admin_router.get("/users/{user_id}/permissions/simulate", summary="Permission simulator")
def simulate(user_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return platform.rbac.simulate(user_id)


# -- feature flags --
@admin_router.post("/flags", summary="Create flag")
def create_flag(payload: FlagCreate = Body(...), platform: PlatformAdmin = Depends(get_platform)):
    try:
        return platform.flags.create(
            payload.key,
            payload.description,
            payload.flag_type,
            payload.default_value,
            payload.rules,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@admin_router.get("/flags", summary="List flags")
def list_flags(platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.flags.list()}


@admin_router.post("/flags/evaluate", summary="Evaluate flag")
def evaluate_flag(
    payload: FlagEvaluate = Body(...), platform: PlatformAdmin = Depends(get_platform)
):
    try:
        return platform.flags.evaluate(
            payload.key, payload.user_id, payload.organization_id, payload.environment
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@admin_router.patch("/flags/{key}", summary="Update flag")
def update_flag(
    key: str, patch: dict[str, Any] = Body(...), platform: PlatformAdmin = Depends(get_platform)
):
    try:
        return platform.flags.update(key, patch)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@admin_router.post("/flags/{key}/kill", summary="Kill switch")
def kill_flag(key: str, platform: PlatformAdmin = Depends(get_platform)):
    try:
        flag = platform.flags.kill(key)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    platform.audit.append("flag_killed", "flag", key)
    return flag


@admin_router.get("/flags/history", summary="Flag history")
def flag_history(key: str | None = Query(None), platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.flags.history(key)}


# -- settings / maintenance --
@admin_router.get("/settings", summary="All settings")
def all_settings(platform: PlatformAdmin = Depends(get_platform)):
    return platform.settings.all()


@admin_router.patch("/settings/{key}", summary="Update setting")
def update_setting(
    key: str, payload: SettingUpdate = Body(...), platform: PlatformAdmin = Depends(get_platform)
):
    try:
        value = platform.settings.update(key, payload.value.get("value"))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    platform.audit.append("setting_changed", "setting", key, details={"value": value})
    return {"key": key, "value": value}


@admin_router.get("/maintenance", summary="Maintenance status")
def maintenance_status(platform: PlatformAdmin = Depends(get_platform)):
    return platform.settings.maintenance_status()


@admin_router.post("/maintenance", summary="Set maintenance mode")
def set_maintenance(
    payload: MaintenanceUpdate = Body(...), platform: PlatformAdmin = Depends(get_platform)
):
    try:
        result = platform.settings.set_maintenance(
            payload.mode, payload.message, payload.starts_at, payload.ends_at
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    platform.audit.append(
        "maintenance_mode_changed",
        "system",
        "maintenance",
        details={"mode": payload.mode, "message": payload.message},
    )
    return result


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


@admin_router.get(
    "/metrics/prometheus", summary="Prometheus exposition", response_class=PlainTextResponse
)
def prometheus(platform: PlatformAdmin = Depends(get_platform)):
    return platform.metrics.render_prometheus()


@admin_router.post("/metrics/record", summary="Record metric")
def record_metric(
    name: str = Body(...),
    value: float = Body(...),
    labels: dict[str, str] | None = Body(None),
    platform: PlatformAdmin = Depends(get_platform),
):
    platform.metrics.record(name, value, labels)
    return {"recorded": True}


@admin_router.get("/traces", summary="Recent traces")
def recent_traces(
    limit: int = Query(50, ge=1, le=500), platform: PlatformAdmin = Depends(get_platform)
):
    return {"data": platform.tracer.recent(limit)}


@admin_router.get("/traces/{trace_id}", summary="Trace detail")
def trace_detail(trace_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.tracer.spans_for_trace(trace_id)}


# -- audit --
@admin_router.get("/audit", summary="Query audit log")
def query_audit(
    action: str | None = Query(None),
    actor_id: str | None = Query(None),
    organization_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    platform: PlatformAdmin = Depends(get_platform),
):
    return {"data": platform.audit.query(action, actor_id, organization_id, limit, offset)}


@admin_router.get("/audit/verify", summary="Verify audit chain")
def verify_audit(platform: PlatformAdmin = Depends(get_platform)):
    return platform.audit.verify_chain()


# -- alerts --
@admin_router.post("/alerts/rules", summary="Create alert rule")
def create_rule(
    payload: AlertRuleCreate = Body(...), platform: PlatformAdmin = Depends(get_platform)
):
    try:
        return platform.alerts.create_rule(
            payload.name,
            payload.metric,
            payload.threshold,
            payload.operator,
            payload.window_seconds,
            payload.severity,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@admin_router.get("/alerts/rules", summary="List alert rules")
def list_rules(platform: PlatformAdmin = Depends(get_platform)):
    return {"data": platform.alerts.list_rules()}


@admin_router.delete("/alerts/rules/{rule_id}", summary="Delete rule")
def delete_rule(rule_id: str, platform: PlatformAdmin = Depends(get_platform)):
    if not platform.alerts.delete_rule(rule_id):
        raise HTTPException(404, "Rule not found")
    return {"deleted": True}


@admin_router.get("/alerts/incidents", summary="List incidents")
def list_incidents(
    status: str | None = Query(None), platform: PlatformAdmin = Depends(get_platform)
):
    return {"data": platform.alerts.incidents(status)}


@admin_router.post("/alerts/incidents/{incident_id}/ack", summary="Acknowledge")
def acknowledge(incident_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.alerts.acknowledge(incident_id), "Incident")


@admin_router.post("/alerts/evaluate", summary="Evaluate metric")
def evaluate_alert(
    metric: str = Body(...),
    value: float = Body(...),
    platform: PlatformAdmin = Depends(get_platform),
):
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
def create_notification(
    payload: NotificationCreate = Body(...), platform: PlatformAdmin = Depends(get_platform)
):
    return platform.notifications.create(
        payload.user_id, payload.title, payload.body, payload.kind, payload.organization_id
    )


@admin_router.get("/notifications", summary="List notifications")
def list_notifications(
    user_id: str | None = Query(None),
    unread_only: bool = Query(False),
    platform: PlatformAdmin = Depends(get_platform),
):
    return {"data": platform.notifications.list(user_id, unread_only)}


@admin_router.post("/notifications/{notification_id}/read", summary="Mark read")
def mark_read(notification_id: str, platform: PlatformAdmin = Depends(get_platform)):
    return _not_found(platform.notifications.mark_read(notification_id), "Notification")


# -- user lifecycle extras --
@admin_router.post("/users/{user_id}/activate", summary="Activate user")
def activate_user(user_id: str, platform: PlatformAdmin = Depends(get_platform)):
    user = _not_found(platform.users.set_active(user_id, True), "User")
    platform.audit.append("user_activated", "user", user_id)
    return user


@admin_router.post("/users/{user_id}/deactivate", summary="Deactivate user")
def deactivate_user(user_id: str, platform: PlatformAdmin = Depends(get_platform)):
    user = _not_found(platform.users.set_active(user_id, False), "User")
    platform.audit.append("user_deactivated", "user", user_id)
    return user


@admin_router.post("/users/{user_id}/move", summary="Move user to organization")
def move_user(
    user_id: str,
    organization_id: str = Body(..., embed=True),
    platform: PlatformAdmin = Depends(get_platform),
):
    user = _not_found(platform.users.update(user_id, {"organization_id": organization_id}), "User")
    platform.audit.append(
        "user_moved", "user", user_id, details={"organization_id": organization_id}
    )
    return user


@admin_router.get("/users/{user_id}/roles", summary="List user roles")
def user_roles(user_id: str, platform: PlatformAdmin = Depends(get_platform)):
    _not_found(platform.users.get(user_id), "User")
    return {"data": platform.rbac.user_roles(user_id)}


@admin_router.post("/users/{user_id}/change-role", summary="Replace user roles")
def change_role(
    user_id: str,
    role_ids: list[str] = Body(..., embed=True),
    platform: PlatformAdmin = Depends(get_platform),
):
    _not_found(platform.users.get(user_id), "User")
    for rid in platform.rbac.user_roles(user_id):
        platform.rbac.unassign_role(user_id, rid["id"])
    try:
        for rid in role_ids:
            platform.rbac.assign_role(user_id, rid)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    platform.audit.append("roles_changed", "user", user_id, details={"roles": role_ids})
    return {"data": platform.rbac.user_roles(user_id)}


# -- roles extras --
@admin_router.patch("/roles/{role_id}", summary="Edit role")
def edit_role(
    role_id: str,
    patch: dict[str, Any] = Body(...),
    platform: PlatformAdmin = Depends(get_platform),
):
    try:
        role = _not_found(platform.rbac.update_role(role_id, patch), "Role")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    platform.audit.append("role_updated", "role", role_id)
    return role


@admin_router.post("/roles/{role_id}/clone", summary="Clone role")
def clone_role(
    role_id: str,
    name: str = Body(..., embed=True),
    platform: PlatformAdmin = Depends(get_platform),
):
    try:
        role = platform.rbac.clone_role(role_id, name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    platform.audit.append("role_cloned", "role", role["id"], details={"from": role_id})
    return role


@admin_router.get("/roles/{role_id}/users", summary="Users with role")
def role_users(role_id: str, platform: PlatformAdmin = Depends(get_platform)):
    try:
        user_ids = platform.rbac.role_users(role_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    users = [u for uid in user_ids if (u := platform.users.get(uid)) is not None]
    return {"data": users}


@admin_router.post("/roles/{role_id}/permissions", summary="Grant permission")
def grant_permission(
    role_id: str,
    code: str = Body(..., embed=True),
    platform: PlatformAdmin = Depends(get_platform),
):
    try:
        platform.rbac.grant_permission(role_id, code)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"granted": code}


@admin_router.delete("/roles/{role_id}/permissions/{code}", summary="Revoke permission")
def revoke_permission(role_id: str, code: str, platform: PlatformAdmin = Depends(get_platform)):
    try:
        ok = platform.rbac.revoke_permission(role_id, code)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not ok:
        raise HTTPException(404, "Permission grant not found")
    return {"revoked": code}


@admin_router.get("/permissions/matrix", summary="Permission matrix")
def permission_matrix(platform: PlatformAdmin = Depends(get_platform)):
    return platform.rbac.permission_matrix()


# -- organizations extras --
@admin_router.post("/organizations/{org_id}/archive", summary="Archive organization")
def archive_org(org_id: str, platform: PlatformAdmin = Depends(get_platform)):
    if not platform.orgs.delete(org_id):
        raise HTTPException(404, "Organization not found")
    platform.audit.append("org_archived", "organization", org_id)
    return {"archived": True}


@admin_router.get("/organizations/{org_id}/users", summary="Organization users")
def org_users(org_id: str, platform: PlatformAdmin = Depends(get_platform)):
    _not_found(platform.orgs.get(org_id), "Organization")
    return {"data": platform.users.list(organization_id=org_id, include_inactive=True)}


# -- audit export --
@admin_router.get("/audit/export", summary="Export audit log")
def export_audit(
    format: str = Query("csv", pattern="^(csv|json)$"),
    action: str | None = Query(None),
    actor_id: str | None = Query(None),
    organization_id: str | None = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    platform: PlatformAdmin = Depends(get_platform),
):
    import csv
    import io
    import json

    entries = platform.audit.query(action, actor_id, organization_id, limit, 0)
    if format == "json":
        return Response(
            content=json.dumps(entries, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit.json"},
        )
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "id",
            "created_at",
            "actor_id",
            "action",
            "resource_type",
            "resource_id",
            "organization_id",
        ],
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(entries)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit.csv"},
    )


# -- alerts extras --
@admin_router.patch("/alerts/rules/{rule_id}", summary="Edit alert rule")
def edit_alert_rule(
    rule_id: str,
    enabled: bool = Body(..., embed=True),
    platform: PlatformAdmin = Depends(get_platform),
):
    rule = _not_found(platform.alerts.set_enabled(rule_id, enabled), "Alert rule")
    platform.audit.append("alert_rule_updated", "alert_rule", rule_id, details={"enabled": enabled})
    return rule


# -- flags extras --
@admin_router.delete("/flags/{key}", summary="Delete flag")
def delete_flag(key: str, platform: PlatformAdmin = Depends(get_platform)):
    if not platform.flags.delete(key):
        raise HTTPException(404, "Flag not found")
    platform.audit.append("flag_deleted", "flag", key)
    return {"deleted": True}


# -- AI administration --
@admin_router.get("/ai/overview", summary="AI platform overview")
def ai_overview(platform: PlatformAdmin = Depends(get_platform)):
    overview: dict[str, Any] = {"providers": ["openai"], "models": ["gpt-4"]}
    try:
        from app.ai.embeddings.manager import EmbeddingManager  # type: ignore

        overview["embedding_model"] = EmbeddingManager().config.model
    except Exception as exc:
        overview["embedding_model"] = f"unavailable: {exc}"
    try:
        from app.ai.rag.rag_pipeline import RAGPipeline  # type: ignore

        overview["retrieval"] = RAGPipeline().get_stats()
    except Exception as exc:
        overview["retrieval"] = {"error": str(exc)[:200]}
    overview["monitoring"] = platform.metrics.platform_snapshot().get("ai", {})
    try:
        overview["tool_count"] = platform.metrics.platform_snapshot().get("ai_tools", 0)
    except Exception:
        overview["tool_count"] = 0
    return overview


@admin_router.get("/ai/prompts", summary="Prompt templates")
def ai_prompts(platform: PlatformAdmin = Depends(get_platform)):
    _ = platform
    try:
        from app.ai.prompts.prompt_manager import PromptManager  # type: ignore

        manager = PromptManager()
        return {
            "data": [
                {
                    "id": pid,
                    "preview": manager._default_prompts.get(pid, "")[:200],
                }
                for pid in manager.get_default_prompt_ids()
            ]
        }
    except Exception as exc:
        raise HTTPException(503, f"Prompt manager unavailable: {exc}") from exc


@admin_router.get("/ai/vectorstore", summary="Vector store stats")
def ai_vectorstore(platform: PlatformAdmin = Depends(get_platform)):
    _ = platform
    try:
        from app.ai.vectorstore.vectorstore import VectorStore  # type: ignore

        store = VectorStore()
        return {
            "backend": store._backend,
            "namespaces": {},
            "record_count": store.get_namespace_count(),
        }
    except Exception as exc:
        raise HTTPException(503, f"Vector store unavailable: {exc}") from exc


# -- jobs extras --
@admin_router.post("/jobs/{task_id}/cancel", summary="Cancel job")
def cancel_job(task_id: str, platform: PlatformAdmin = Depends(get_platform)):
    try:
        from app.workers.celery_app import celery_app  # type: ignore

        if celery_app is None:
            raise HTTPException(503, "Job system not configured")
        celery_app.control.revoke(task_id, terminate=True)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"Cannot reach job system: {exc}") from exc
    platform.audit.append("job_cancelled", "job", task_id)
    return {"cancelled": task_id}


@admin_router.post("/jobs/{task_id}/retry", summary="Retry job")
def retry_job(
    task_id: str,
    task_name: str = Body(""),
    task_args: list[Any] = Body(default_factory=list),
    task_kwargs: dict[str, Any] = Body(default_factory=dict),
    platform: PlatformAdmin = Depends(get_platform),
):
    if not task_name:
        raise HTTPException(400, "task_name is required to re-queue a job")
    try:
        from app.workers.celery_app import celery_app  # type: ignore

        if celery_app is None:
            raise HTTPException(503, "Job system not configured")
        result = celery_app.send_task(task_name, args=task_args, kwargs=task_kwargs)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"Cannot reach job system: {exc}") from exc
    platform.audit.append("job_retried", "job", task_id, details={"new_id": result.id})
    return {"retried": task_id, "new_task_id": result.id}
