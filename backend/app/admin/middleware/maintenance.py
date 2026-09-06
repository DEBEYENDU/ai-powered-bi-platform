"""Maintenance-mode enforcement middleware.

Semantics (single source of truth — matches the admin API contract):
- ``off``:         everything allowed.
- ``readonly``:    safe methods (GET/HEAD/OPTIONS) allowed; writes blocked
                   EXCEPT the maintenance-management endpoints (the escape
                   hatch: without it a readonly platform can never be
                   switched back) and requests bearing an override token.
- ``maintenance``: everything blocked EXCEPT health checks, API docs, the
                   maintenance-management endpoints, and override-token
                   requests.

Exempt paths (prefix match):
- ``/health`` — liveness/readiness probes must never be blocked.
- ``/docs``, ``/redoc``, ``/openapi.json`` — operators need API docs
  during incidents.
- ``/admin/maintenance``, ``/api/v1/admin/maintenance`` — mode status,
  mode changes, and override-token minting. Without this exemption the
  platform deadlocks: the only way out of readonly/maintenance would
  itself be blocked with 503.

Override: ``X-Admin-Override`` header matching a minted token bypasses all
blocking (emergency access). Tokens are minted via the exempt endpoint above.

All decisions are logged with the SettingsService instance id so singleton
divergence is visible immediately.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.logging import get_logger

log = get_logger(__name__)

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# Prefixes that are never blocked, in any mode.
ALWAYS_ALLOWED_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)

# Maintenance-management endpoints: the escape hatch. Must stay reachable in
# readonly AND maintenance modes or the platform deadlocks (observed bug:
# POST /admin/maintenance returned 503 while trying to leave readonly mode).
MAINTENANCE_ENDPOINT_PREFIXES = (
    "/admin/maintenance",
    "/api/v1/admin/maintenance",
)


def _is_exempt(path: str) -> tuple[bool, str]:
    for prefix in MAINTENANCE_ENDPOINT_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return True, "maintenance-endpoint"
    for prefix in ALWAYS_ALLOWED_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return True, "health-or-docs"
    return False, ""


class MaintenanceMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings_service=None):  # type: ignore[no-untyped-def]
        super().__init__(app)
        # Optional explicit injection (tests). Production path resolves the
        # process-wide singleton per request (see _resolve_settings).
        self._settings = settings_service

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        settings = self._resolve_settings()
        if settings is None:
            log.warning("maintenance_bypass_no_settings", path=request.url.path)
            return await call_next(request)
        status = settings.maintenance_status()
        mode = status.get("mode", "off")
        path = request.url.path
        method = request.method
        sid = id(settings)

        exempt, reason = _is_exempt(path)
        if exempt:
            log.info(
                "maintenance_allow",
                method=method,
                path=path,
                mode=mode,
                reason=reason,
                settings_id=sid,
            )
            return await call_next(request)

        if mode == "off":
            return await call_next(request)

        override = request.headers.get("X-Admin-Override")
        if override and settings.check_override(override):
            log.info(
                "maintenance_allow",
                method=method,
                path=path,
                mode=mode,
                reason="override-token",
                settings_id=sid,
            )
            return await call_next(request)

        if mode == "readonly" and method in SAFE_METHODS:
            return await call_next(request)

        log.warning(
            "maintenance_block",
            method=method,
            path=path,
            mode=mode,
            settings_id=sid,
        )
        detail = status.get("message") or (
            "Platform is in maintenance mode."
            if mode == "maintenance"
            else "Platform is read-only."
        )
        return JSONResponse(
            status_code=503,
            content={"title": "Maintenance", "status": 503, "detail": detail},
        )

    def _resolve_settings(self):  # type: ignore[no-untyped-def]
        # Per-request resolution against the single process-wide singleton.
        # There is exactly one PlatformAdmin (see services/platform.py
        # get_platform); resolving here (not at import) guarantees the
        # middleware can never hold a stale copy.
        if self._settings is not None:
            return self._settings
        try:
            from app.admin.services.platform import get_platform

            return get_platform().settings
        except Exception:
            return None
