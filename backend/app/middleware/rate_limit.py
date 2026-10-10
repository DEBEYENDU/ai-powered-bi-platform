"""Rate limiting middleware — Redis-backed with in-memory fallback, tenant-aware."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-tenant + per-IP rate limiting middleware.

    Uses Redis when available; falls back to in-memory sliding window for
    local development. Tenant-scoped keys when authenticated, IP-only fallback.
    """

    def __init__(
        self,
        app: Any,
        requests_per_minute: int = 120,
        redis_url: str | None = None,
    ) -> None:
        super().__init__(app)
        self.rpm = requests_per_minute
        self._redis: Any = None
        self._memory: dict[str, list[float]] = defaultdict(list)
        if redis_url:
            # Probe the socket first: redis-py retries a dead broker for ~4s,
            # which used to stall application startup.
            from app.core.net import tcp_reachable

            reachable, _where = tcp_reachable(redis_url, 0.3)
            if reachable:
                try:
                    import redis  # type: ignore

                    self._redis = redis.Redis.from_url(
                        redis_url, socket_connect_timeout=2, decode_responses=True
                    )
                    self._redis.ping()
                except Exception:
                    self._redis = None  # fall back to memory

    def _extract_tenant_id(self, request: Request) -> str | None:
        """Try to extract tenant_id from JWT in Authorization header."""
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return None
        try:
            import jwt  # type: ignore
            from app.core.config import get_settings
            token = auth[7:]
            payload = jwt.decode(token, get_settings().jwt_secret_key, algorithms=[get_settings().jwt_algorithm])
            return payload.get("organization_id")
        except Exception:
            return None

    def _is_suspended(self, tenant_id: str) -> bool:
        """Check if tenant is suspended via cache or DB."""
        if not tenant_id:
            return False
        try:
            from sqlalchemy import text
            from app.db.session import get_engine
            with get_engine().connect() as conn:
                result = conn.execute(
                    text("SELECT status FROM organizations WHERE id = :tid"),
                    {"tid": tenant_id},
                )
                row = result.fetchone()
                return row and row[0] in ("suspended", "deleted")
        except Exception:
            return False

    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        path = request.url.path
        if path in ("/health", "/health/db", "/health/redis", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        tenant_id = self._extract_tenant_id(request)
        client_ip = request.client.host if request.client else "unknown"

        # Platform-admin tenant lifecycle endpoints must stay reachable so a
        # suspended tenant can be reactivated (suspension must not deadlock).
        is_tenant_admin_path = "/admin/tenants" in path
        if tenant_id and not is_tenant_admin_path and self._is_suspended(tenant_id):
            return JSONResponse(
                status_code=403,
                content={"error": "tenant_suspended", "detail": "Your organization has been suspended."},
            )

        key = f"rl:t:{tenant_id}:{client_ip}" if tenant_id else f"rl:{client_ip}"
        now = time.time()
        window = 60.0

        if self._redis:
            try:
                pipe = self._redis.pipeline()
                pipe.zremrangebyscore(key, 0, now - window)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, int(window) + 1)
                results = pipe.execute()
                count = results[2]
            except Exception:
                count = self._check_memory(key, now, window)
        else:
            count = self._check_memory(key, now, window)

        if count > self.rpm:
            retry_after = int(window - (now - self._memory[key][0])) if self._memory.get(key) else 60
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limit_exceeded", "retry_after": retry_after, "limit": self.rpm},
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.rpm - count))
        return response

    def _check_memory(self, key: str, now: float, window: float) -> int:
        entries = self._memory[key]
        cutoff = now - window
        self._memory[key] = [t for t in entries if t > cutoff]
        self._memory[key].append(now)
        return len(self._memory[key])
