from __future__ import annotations
from typing import Any, Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TenantContextMiddleware(BaseHTTPMiddleware):
    SKIP_PATHS = frozenset({
        "/health", "/health/db", "/health/redis",
        "/docs", "/redoc", "/openapi.json",
        "/admin/maintenance",
    })

    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        path = request.url.path
        if path in self.SKIP_PATHS or not path.startswith("/api/"):
            return await call_next(request)
        return await call_next(request)
