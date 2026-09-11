"""Workflow trigger handlers."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.workflows.schemas import TriggerConfig, TriggerType

log = get_logger("workflow.triggers")


def compute_next_run(trigger: TriggerConfig, last_run: datetime | None = None) -> datetime | None:
    """Compute the next scheduled run time based on trigger configuration."""
    now = datetime.utcnow()
    base = last_run or now

    if trigger.type == TriggerType.MANUAL:
        return None

    if trigger.type == TriggerType.DAILY:
        if trigger.time:
            h, m = (int(x) for x in trigger.time.split(":"))
            next_day = base + timedelta(days=1)
            return next_day.replace(hour=h, minute=m, second=0, microsecond=0)
        return base + timedelta(days=1)

    if trigger.type == TriggerType.WEEKLY:
        day_map = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        target_day = day_map.get(trigger.day_of_week.lower(), 0)
        h, m = (int(x) for x in trigger.time.split(":")) if trigger.time else (9, 0)
        days_ahead = (target_day - base.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (base + timedelta(days=days_ahead)).replace(
            hour=h, minute=m, second=0, microsecond=0
        )

    if trigger.type == TriggerType.MONTHLY:
        target_day = trigger.day_of_month or 1
        month = base.month + 1
        year = base.year
        if month > 12:
            month = 1
            year += 1
        return datetime(year, month, target_day, 9, 0, 0)

    if trigger.type == TriggerType.QUARTERLY:
        month = base.month + 3
        year = base.year
        while month > 12:
            month -= 12
            year += 1
        return datetime(year, month, 1, 9, 0, 0)

    if trigger.type == TriggerType.CRON:
        # Basic cron parsing (minute hour day month weekday)
        return _parse_cron_next(trigger.cron_expression, now)

    if trigger.type == TriggerType.SCHEDULED:
        # Use configured datetime
        if trigger.time:
            return base + timedelta(hours=1)
        return None

    return None


def _parse_cron_next(expression: str, now: datetime) -> datetime | None:
    """Parse a simple cron expression and compute next run."""
    parts = expression.strip().split()
    if len(parts) < 5:
        return None

    minute, hour, day, month, weekday = parts
    next_run = now + timedelta(minutes=1)
    next_run = next_run.replace(second=0, microsecond=0)

    # Try up to 366 days ahead
    for _ in range(366 * 24 * 60):
        if (
            _match_cron_field(minute, next_run.minute)
            and _match_cron_field(hour, next_run.hour)
            and _match_cron_field(day, next_run.day)
            and _match_cron_field(month, next_run.month)
            and _match_cron_field(weekday, next_run.weekday())
        ):
            return next_run
        next_run += timedelta(minutes=1)

    return None


def _match_cron_field(field: str, value: int) -> bool:
    """Check if a cron field matches the given value."""
    if field == "*":
        return True
    if "-" in field:
        lo, hi = (int(x) for x in field.split("-"))
        return lo <= value <= hi
    if "," in field:
        return value in {int(x) for x in field.split(",")}
    if "/" in field:
        _, step = field.split("/")
        return value % int(step) == 0
    return int(field) == value


def should_trigger_now(trigger: TriggerConfig, last_run: datetime | None = None) -> bool:
    """Determine if a trigger should fire right now."""
    if trigger.type == TriggerType.MANUAL:
        return False

    next_run = compute_next_run(trigger, last_run)
    if next_run is None:
        return False

    now = datetime.utcnow()
    return now >= next_run
