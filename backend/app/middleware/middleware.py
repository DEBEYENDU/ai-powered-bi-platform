"""HTTP middleware: request IDs + timing, security headers.

Rate limiting and auth live in dependencies / routers so they stay testable
without a running server; CORS is configured on the app in ``main.py``.
"""

from __future__ import annotations

import contextlib
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, request_id_ctx

log = get_logger(__name__)

# Patterns for normalizing high-cardinality URL segments into bounded labels.
# These ensure /users/123, /users/abc-def all map to /users/{id}.
_PATH_PARAM_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_NUMERIC_RE = re.compile(r"\b\d+\b")


def _normalize_route(path: str) -> str:
    """Collapse high-cardinality URL segments into bounded route labels.

    Examples:
        /users/123         -> /users/{id}
        /users/abc-def-123 -> /users/{id}
        /orgs/o123/quota   -> /orgs/{id}/quota
        /admin/users       -> /admin/users   (no change)
    """
    normalized = _PATH_PARAM_RE.sub("{id}", path)
    normalized = _NUMERIC_RE.sub("{id}", normalized)
    return normalized


def _record_request_metrics(latency_ms: float, status_code: int, route: str) -> None:
    # Lazy import: keeps core middleware decoupled from the admin module and
    # never breaks request handling if metrics are unavailable.
    with contextlib.suppress(Exception):
        from app.admin.services.platform import get_platform

        get_platform().metrics.record_request(latency_ms, status_code, route)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_ctx.set(request_id)
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-ms"] = str(elapsed_ms)

        # Normalize route for bounded metric labels.
        route = _normalize_route(request.url.path)
        log.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=elapsed_ms,
        )
        _record_request_metrics(elapsed_ms, response.status_code, route)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            ),
        )
        return response
