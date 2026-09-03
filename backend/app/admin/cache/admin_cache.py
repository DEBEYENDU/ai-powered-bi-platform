"""Admin cache namespaces (health snapshots, metrics windows).

Backed by the shared ``CacheService`` so Redis is reused when available.
"""

from __future__ import annotations

from app.cache.service import CacheService


def get_admin_cache() -> CacheService:
    return CacheService(namespace="admin", default_ttl=60.0)
