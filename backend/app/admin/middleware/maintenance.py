"""Maintenance-mode enforcement middleware.

- mode off: passthrough.
- readonly: blocks POST/PUT/PATCH/DELETE except /admin/* with override token.
- maintenance: blocks everything except /health* and /admin/* with override.
Admin override: ``X-Admin-Override`` header matching a minted token.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class MaintenanceMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings_service=None):  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._settings = settings_service

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        settings = self._resolve_settings()
        if settings is None:
            return await call_next(request)
        status = settings.maintenance_status()
        mode = status.get("mode", "off")
        path = request.url.path
        if mode == "off" or path.startswith("/health"):
            return await call_next(request)
        override = request.headers.get("X-Admin-Override")
        if override and settings.check_override(override):
            return await call_next(request)
        if mode == "readonly" and request.method not in WRITE_METHODS:
            return await call_next(request)
        return JSONResponse(
            status_code=503,
            content={
                "title": "Maintenance",
                "status": 503,
                "detail": status.get("message") or "Platform is in maintenance mode. Reads only.",
            },
        )

    def _resolve_settings(self):  # type: ignore[no-untyped-def]
        if self._settings is not None:
            return self._settings
        try:
            from app.admin.services.platform import get_platform

            return get_platform().settings
        except Exception:
            return None
