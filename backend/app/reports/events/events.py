"""Report event system + audit log.

Events: report_generated, report_scheduled, report_delivered, report_failed,
template_updated, approval_requested, approval_granted, report_archived.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class ReportEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{datetime.utcnow().timestamp()}")
    event_type: str
    report_id: Optional[str] = None
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[ReportEvent], Any]]] = defaultdict(list)
        self._events: List[ReportEvent] = []

    def subscribe(self, event_type: str, handler: Callable[[ReportEvent], Any]) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, report_id: Optional[str] = None,
                user_id: Optional[str] = None, organization_id: Optional[str] = None,
                details: Optional[Dict[str, Any]] = None) -> ReportEvent:
        event = ReportEvent(event_type=event_type, report_id=report_id, user_id=user_id,
                            organization_id=organization_id, details=details or {})
        self._events.append(event)
        for handler in self._subscribers.get(event_type, []):
            try:
                handler(event)
            except Exception:
                continue
        return event

    def history(self, report_id: Optional[str] = None, limit: int = 100) -> List[ReportEvent]:
        events = self._events if report_id is None else [e for e in self._events if e.report_id == report_id]
        return events[-limit:]
