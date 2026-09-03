"""In-app notification service (alert fan-out target, admin notices).

Email/SMS delivery is intentionally out of scope here (Notification System is
a separate future phase); this service manages in-app notifications with
read tracking, plus an outbox hook the future system can consume.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


class NotificationService:
    def __init__(self, on_create: Optional[Callable[[Dict[str, Any]], Any]] = None) -> None:
        self._items: Dict[str, Dict[str, Any]] = {}
        self._on_create = on_create

    def create(self, user_id: str, title: str, body: str = "", kind: str = "info",
               organization_id: Optional[str] = None) -> Dict[str, Any]:
        item = {"id": str(uuid4()), "user_id": user_id,
                "organization_id": organization_id, "kind": kind,
                "title": title, "body": body, "read": False,
                "created_at": datetime.utcnow().isoformat()}
        self._items[item["id"]] = item
        if self._on_create:
            try:
                self._on_create(item)
            except Exception:
                pass
        return item

    def notify_alert(self, incident: Dict[str, Any], user_ids: Optional[List[str]] = None) -> int:
        count = 0
        for uid in user_ids or ["admin"]:
            self.create(uid, f"[{incident.get('severity', 'warning')}] {incident.get('metric')}",
                        f"Observed {incident.get('observed_value')}", kind="alert")
            count += 1
        return count

    def list(self, user_id: Optional[str] = None, unread_only: bool = False,
             limit: int = 50) -> List[Dict[str, Any]]:
        items = list(self._items.values())
        if user_id:
            items = [i for i in items if i["user_id"] == user_id]
        if unread_only:
            items = [i for i in items if not i["read"]]
        return sorted(items, key=lambda i: i["created_at"], reverse=True)[:limit]

    def mark_read(self, notification_id: str) -> Optional[Dict[str, Any]]:
        item = self._items.get(notification_id)
        if item:
            item["read"] = True
        return item

    def unread_count(self, user_id: str) -> int:
        return sum(1 for i in self._items.values()
                   if i["user_id"] == user_id and not i["read"])
