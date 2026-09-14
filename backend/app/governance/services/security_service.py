"""Security event and monitoring service."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.governance.models.policy import SecurityEvent

log = get_logger("governance.security")


class SecurityService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record_event(
        self,
        organization_id: str,
        event_type: str,
        severity: str,
        actor_id: str = "",
        resource_type: str = "",
        resource_id: str = "",
        action: str = "",
        outcome: str = "denied",
        details: dict | None = None,
        source_ip: str = "",
        request_id: str = "",
        actor_email: str = "",
    ) -> SecurityEvent:
        event = SecurityEvent(
            organization_id=organization_id,
            event_type=event_type,
            severity=severity,
            actor_id=actor_id,
            actor_email=actor_email,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            outcome=outcome,
            details=details or {},
            source_ip=source_ip,
            request_id=request_id,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        log.warning("security_event", event_type=event_type, severity=severity, actor=actor_id)
        return event

    def get_events(
        self,
        organization_id: str,
        event_type: str | None = None,
        severity: str | None = None,
        limit: int = 100,
    ) -> list[SecurityEvent]:
        stmt = select(SecurityEvent).where(SecurityEvent.organization_id == organization_id)
        if event_type:
            stmt = stmt.where(SecurityEvent.event_type == event_type)
        if severity:
            stmt = stmt.where(SecurityEvent.severity == severity)
        return list(
            self.db.scalars(stmt.order_by(SecurityEvent.created_at.desc()).limit(limit).all())
        )

    def get_summary(self, organization_id: str, hours: int = 24) -> dict[str, Any]:
        since = datetime.utcnow() - timedelta(hours=hours)
        stmt = select(SecurityEvent).where(
            SecurityEvent.organization_id == organization_id,
            SecurityEvent.created_at >= since,
        )
        events = list(self.db.scalars(stmt).all())

        by_severity: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for e in events:
            by_severity[e.severity] = by_severity.get(e.severity, 0) + 1
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1

        return {
            "total_events": len(events),
            "by_severity": by_severity,
            "by_type": by_type,
            "period_hours": hours,
        }

    def check_repeated_failures(
        self, actor_id: str, organization_id: str, threshold: int = 5, window_minutes: int = 15
    ) -> bool:
        since = datetime.utcnow() - timedelta(minutes=window_minutes)
        stmt = (
            select(func.count())
            .select_from(SecurityEvent)
            .where(
                SecurityEvent.actor_id == actor_id,
                SecurityEvent.organization_id == organization_id,
                SecurityEvent.event_type == "auth_failure",
                SecurityEvent.created_at >= since,
            )
        )
        count = self.db.scalar(stmt) or 0
        if count >= threshold:
            self.record_event(
                organization_id=organization_id,
                event_type="repeated_auth_failure",
                severity="HIGH",
                actor_id=actor_id,
                action="login",
                outcome="blocked",
                details={"attempts": count, "window_minutes": window_minutes},
            )
            return True
        return False
