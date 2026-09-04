"""Immutable audit log with hash-chain tamper detection.

Append-only by design: no update/delete methods exist. Each entry stores the
hash of the previous entry; ``verify_chain`` recomputes the chain to detect
tampering. Swap the in-memory list for ``AuditLogRecord`` persistence without
changing callers.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import uuid4


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
        prev = self._entries[-1]["entry_hash"] if self._entries else "GENESIS"
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
        return entry

    def query(
        self,
        action: str | None = None,
        actor_id: str | None = None,
        organization_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        results = self._entries
        if action:
            results = [e for e in results if e["action"] == action]
        if actor_id:
            results = [e for e in results if e["actor_id"] == actor_id]
        if organization_id:
            results = [e for e in results if e["organization_id"] == organization_id]
        return list(reversed(results[offset : offset + limit]))

    def verify_chain(self) -> dict[str, Any]:
        prev = "GENESIS"
        for idx, entry in enumerate(self._entries):
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
        return {"valid": True, "entries_checked": len(self._entries)}
