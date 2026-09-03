"""Thin persistence adapters (in-memory; swap for SQLAlchemy models).

All repositories below delegate to the services' stores today and expose a
``BaseRepository``-shaped interface so ``app.db``-backed implementations can
replace them without touching routers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class AdminRepository:
    """Generic record store used by admin sub-services in tests and minimal envs."""

    def __init__(self) -> None:
        self._records: Dict[str, Dict[str, Any]] = {}

    def save(self, record_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
        self._records[record_id] = dict(record)
        return self._records[record_id]

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        record = self._records.get(record_id)
        return dict(record) if record else None

    def list(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return [dict(r) for r in list(self._records.values())[offset:offset + limit]]

    def delete(self, record_id: str) -> bool:
        return self._records.pop(record_id, None) is not None
