"""Immutable audit log with hash-chain tamper detection.

Append-only by design: no update/delete methods exist. Each entry stores the
hash of the previous entry; ``verify_chain`` recomputes the chain to detect
tampering. Swap the in-memory list for ``AuditLogRecord`` persistence without
changing callers.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.admin.repositories import db_store


def _entry_hash(
    prev_hash: str, action: str, resource: str, details: dict[str, Any], created_at: str
) -> str:
    payload = json.dumps(
        {
            "prev": prev_hash,
            "action": action,
            "resource": resource,
            "details": details,
            "at": created_at,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class AuditService:
    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    def append(
        self,
        action: str,
        resource_type: str = "",
        resource_id: str = "",
        actor_id: str | None = None,
        organization_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        prev = self._last_hash()
        created_at = datetime.utcnow().isoformat()
        entry = {
            "id": str(uuid4()),
            "organization_id": organization_id,
            "actor_id": actor_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "prev_hash": prev,
            "entry_hash": _entry_hash(
                prev, action, f"{resource_type}:{resource_id}", details or {}, created_at
            ),
            "created_at": created_at,
        }
        self._entries.append(entry)
        with contextlib.suppress(Exception):
            db_store.audit_insert(entry)
        return entry

    def _last_hash(self) -> str:
        if self._entries:
            return self._entries[-1]["entry_hash"]
        with contextlib.suppress(Exception):
            rows = db_store.audit_query_db(limit=1)
            if rows:
                for row in rows:
                    self._entries.append(row)
                return rows[0]["entry_hash"]
        return "GENESIS"

    def query(
        self,
        action: str | None = None,
        actor_id: str | None = None,
        organization_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        def _matches(entry: dict[str, Any]) -> bool:
            return (
                (action is None or entry.get("action") == action)
                and (actor_id is None or entry.get("actor_id") == actor_id)
                and (organization_id is None or entry.get("organization_id") == organization_id)
            )

        rows = None
        with contextlib.suppress(Exception):
            rows = db_store.audit_query_db(action, actor_id, organization_id, limit, offset)

        if rows is not None:
            known = {r["id"] for r in rows}
            fresh = [e for e in reversed(self._entries) if e["id"] not in known and _matches(e)]
            return (fresh + list(rows))[:limit]
        results = [e for e in self._entries if _matches(e)]
        return list(reversed(results[offset : offset + limit]))

    def _full_history_asc(self) -> list[dict[str, Any]]:
        """Complete chronological history (DB + memory, deduplicated)."""
        rows = None
        with contextlib.suppress(Exception):
            rows = db_store.audit_query_db(limit=100000)
        if rows is None:
            return sorted(self._entries, key=lambda e: e["created_at"])
        known = {r["id"] for r in rows}
        combined = list(rows) + [e for e in self._entries if e["id"] not in known]
        return sorted(combined, key=lambda e: e["created_at"])

    def verify_chain(self) -> dict[str, Any]:
        history = self._full_history_asc()
        prev = "GENESIS"
        for idx, entry in enumerate(history):
            expected = _entry_hash(
                prev,
                entry["action"],
                f"{entry['resource_type']}:{entry['resource_id']}",
                entry["details"],
                entry["created_at"],
            )
            if entry["prev_hash"] != prev or entry["entry_hash"] != expected:
                return {"valid": False, "broken_at_index": idx, "entries_checked": idx}
            prev = entry["entry_hash"]
        return {"valid": True, "entries_checked": len(history)}
