"""Caching system for AI Business Assistant."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CacheEntry(BaseModel):
    key: str
    value: Any
    ttl: float = Field(..., description="Time to live in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        elapsed = (datetime.utcnow() - self.created_at).total_seconds()
        return elapsed > self.ttl

    @property
    def remaining_ttl(self) -> float:
        elapsed = (datetime.utcnow() - self.created_at).total_seconds()
        return max(0.0, self.ttl - elapsed)


class AICache:
    """In-memory cache for AI assistant operations."""

    def __init__(self, default_ttl: float = 300.0, max_entries: int = 10000) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._max_entries = max_entries
        self._hit_count = 0
        self._miss_count = 0

    def get(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            self._miss_count += 1
            return None
        if entry.is_expired:
            del self._cache[key]
            self._miss_count += 1
            return None
        entry.access_count += 1
        self._hit_count += 1
        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if len(self._cache) >= self._max_entries:
            self._evict()
        self._cache[key] = CacheEntry(
            key=key,
            value=value,
            ttl=ttl or self._default_ttl,
            metadata=metadata or {},
        )

    def invalidate(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def invalidate_pattern(self, pattern: str) -> int:
        import re

        regex = re.compile(pattern.replace("*", ".*"))
        count = 0
        keys_to_remove = [k for k in self._cache if regex.match(k)]
        for k in keys_to_remove:
            del self._cache[k]
            count += 1
        return count

    def clear(self) -> None:
        self._cache.clear()
        self._hit_count = 0
        self._miss_count = 0

    def get_stats(self) -> dict[str, Any]:
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0.0
        expired = sum(1 for e in self._cache.values() if e.is_expired)
        return {
            "total_entries": len(self._cache),
            "hits": self._hit_count,
            "misses": self._miss_count,
            "hit_rate": round(hit_rate, 4),
            "expired_entries": expired,
        }

    def _evict(self) -> None:
        sorted_entries = sorted(self._cache.items(), key=lambda x: x[1].access_count)
        to_remove = max(1, len(sorted_entries) // 10)
        for key, _ in sorted_entries[:to_remove]:
            del self._cache[key]

    def _make_key(self, prefix: str, **kwargs) -> str:
        content = f"{prefix}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]


def conversation_cache_key(
    conversation_id: str,
    user_id: str,
    query_hash: str,
) -> str:
    return f"conv:{conversation_id}:{user_id}:{query_hash}"


def embedding_cache_key(text: str, model: str) -> str:
    return f"emb:{model}:{hashlib.sha256(text.encode()).hexdigest()[:24]}"


def prompt_cache_key(template_id: str, variables_hash: str) -> str:
    return f"prompt:{template_id}:{variables_hash}"


def retrieval_cache_key(query_hash: str, namespace: str) -> str:
    return f"retrieval:{namespace}:{query_hash}"


def tool_cache_key(tool_name: str, params_hash: str) -> str:
    return f"tool:{tool_name}:{params_hash}"


def response_cache_key(request_id: str, query_hash: str) -> str:
    return f"response:{request_id}:{query_hash}"
