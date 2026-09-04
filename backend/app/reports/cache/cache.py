"""Report cache (TTL + key strategy). Reuses the same pattern as ai/cache."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any


class ReportCache:
    def __init__(self, default_ttl: float = 300.0, max_entries: int = 2000) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._default_ttl = default_ttl
        self._max_entries = max_entries

    def key(self, prefix: str, **kwargs: Any) -> str:
        raw = f"{prefix}:{json.dumps(kwargs, sort_keys=True, default=str)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if (datetime.utcnow() - entry["at"]).total_seconds() > entry["ttl"]:
            del self._store[key]
            return None
        return entry["value"]

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        if len(self._store) >= self._max_entries:
            oldest = min(self._store, key=lambda k: self._store[k]["at"])
            del self._store[oldest]
        self._store[key] = {
            "value": value,
            "at": datetime.utcnow(),
            "ttl": ttl or self._default_ttl,
        }

    def invalidate_report(self, report_id: str) -> int:
        doomed = [k for k, v in self._store.items() if report_id in str(v.get("value", ""))]
        for k in doomed:
            del self._store[k]
        return len(doomed)
