"""Report scheduling service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session


class ScheduleService:
    """Manage report scheduling: create, pause, resume, list."""

    def __init__(self, engine: Engine, db: Session) -> None:
        self._engine = engine
        self._db = db

    def create_schedule(
        self,
        report_id: str,
        frequency: str,
        cron_expression: str = "",
        timezone_str: str = "UTC",
        recipients: list[str] | None = None,
        formats: list[str] | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        """Create a schedule for a report."""
        import uuid
        schedule_id = str(uuid.uuid4())
        try:
            self._db.execute(
                text("""
                    INSERT INTO ai_report_schedules (id, report_id, frequency,
                        cron_expression, timezone, recipients, formats, enabled,
                        created_at)
                    VALUES (:id, :report_id, :freq, :cron, :tz, :recipients, :formats, :enabled, :now)
                """),
                {
                    "id": schedule_id,
                    "report_id": report_id,
                    "freq": frequency,
                    "cron": cron_expression,
                    "tz": timezone_str,
                    "recipients": recipients or [],
                    "formats": formats or ["pdf"],
                    "enabled": enabled,
                    "now": datetime.now(UTC),
                },
            )
            self._db.commit()
            return {"id": schedule_id, "report_id": report_id, "frequency": frequency, "enabled": enabled}
        except Exception:  # noqa: BLE001
            self._db.rollback()
            return {"error": "Failed to create schedule"}

    def list_schedules(self, report_id: str | None = None) -> list[dict[str, Any]]:
        """List schedules, optionally filtered by report."""
        try:
            if report_id:
                result = self._db.execute(
                    text("SELECT id, report_id, frequency, timezone, enabled FROM ai_report_schedules WHERE report_id = :rid"),
                    {"rid": report_id},
                )
            else:
                result = self._db.execute(
                    text("SELECT id, report_id, frequency, timezone, enabled FROM ai_report_schedules LIMIT 100")
                )
            return [
                {"id": str(r[0]), "report_id": str(r[1]), "frequency": r[2], "timezone": r[3], "enabled": r[4]}
                for r in result.fetchall()
            ]
        except Exception:  # noqa: BLE001
            return []

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        try:
            self._db.execute(text("DELETE FROM ai_report_schedules WHERE id = :id"), {"id": schedule_id})
            self._db.commit()
            return True
        except Exception:  # noqa: BLE001
            self._db.rollback()
            return False
