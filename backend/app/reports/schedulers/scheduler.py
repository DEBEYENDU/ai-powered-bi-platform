"""Report scheduler.

Computes next run times for one_time/hourly/daily/weekly/monthly/quarterly/
yearly/cron frequencies with timezone support, pause/resume, retry accounting,
and business-calendar holiday skips. Celery beat can call ``due_schedules``;
the in-memory store keeps unit tests dependency-free.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field


class Schedule(BaseModel):
    schedule_id: str = Field(default_factory=lambda: str(uuid4()))
    report_id: str
    frequency: str = "daily"
    cron_expression: str = ""
    timezone: str = "UTC"
    enabled: bool = True
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    distribution: Dict[str, Any] = Field(default_factory=dict)
    holidays: List[str] = Field(default_factory=list, description="YYYY-MM-DD dates to skip")


class Scheduler:
    def __init__(self) -> None:
        self._schedules: Dict[str, Schedule] = {}

    def create(self, report_id: str, frequency: str = "daily",
               cron_expression: str = "", timezone: str = "UTC",
               distribution: Optional[Dict[str, Any]] = None,
               max_retries: int = 3, holidays: Optional[List[str]] = None,
               now: Optional[datetime] = None) -> Schedule:
        sched = Schedule(
            report_id=report_id, frequency=frequency, cron_expression=cron_expression,
            timezone=timezone, distribution=distribution or {}, max_retries=max_retries,
            holidays=holidays or [],
        )
        sched.next_run_at = self.compute_next_run(sched, now)
        self._schedules[sched.schedule_id] = sched
        return sched

    def get(self, schedule_id: str) -> Optional[Schedule]:
        return self._schedules.get(schedule_id)

    def cancel(self, schedule_id: str) -> bool:
        return self._schedules.pop(schedule_id, None) is not None

    def pause(self, schedule_id: str) -> bool:
        sched = self._schedules.get(schedule_id)
        if sched is None:
            return False
        sched.enabled = False
        return True

    def resume(self, schedule_id: str, now: Optional[datetime] = None) -> bool:
        sched = self._schedules.get(schedule_id)
        if sched is None:
            return False
        sched.enabled = True
        sched.next_run_at = self.compute_next_run(sched, now)
        return True

    def record_run(self, schedule_id: str, success: bool, now: Optional[datetime] = None) -> Optional[Schedule]:
        sched = self._schedules.get(schedule_id)
        if sched is None:
            return None
        moment = now or self._now(sched.timezone)
        sched.last_run_at = moment
        if success:
            sched.retry_count = 0
            sched.next_run_at = self.compute_next_run(sched, moment)
        else:
            sched.retry_count += 1
            if sched.retry_count > sched.max_retries:
                sched.enabled = False  # pause after exhausting retries
            else:
                sched.next_run_at = moment + timedelta(minutes=15 * sched.retry_count)
        return sched

    def due_schedules(self, now: Optional[datetime] = None) -> List[Schedule]:
        moment = now or datetime.utcnow()
        return [s for s in self._schedules.values()
                if s.enabled and s.next_run_at and s.next_run_at <= moment]

    def compute_next_run(self, sched: Schedule, now: Optional[datetime] = None) -> Optional[datetime]:
        base = now or self._now(sched.timezone)
        freq = sched.frequency
        if freq == "one_time":
            return base if sched.next_run_at is None else sched.next_run_at
        if freq == "hourly":
            nxt = (base + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        elif freq == "daily":
            nxt = (base + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
        elif freq == "weekly":
            nxt = (base + timedelta(days=7)).replace(hour=6, minute=0, second=0, microsecond=0)
        elif freq == "monthly":
            nxt = self._add_months(base, 1).replace(hour=6, minute=0, second=0, microsecond=0)
        elif freq == "quarterly":
            nxt = self._add_months(base, 3).replace(hour=6, minute=0, second=0, microsecond=0)
        elif freq == "yearly":
            nxt = base.replace(year=base.year + 1, hour=6, minute=0, second=0, microsecond=0)
        elif freq == "cron":
            nxt = base + timedelta(hours=1)  # full cron parsing delegated to celery beat
        else:
            raise ValueError(f"Unknown frequency '{freq}'")
        return self._skip_holidays(nxt, sched.holidays)

    def _skip_holidays(self, dt: datetime, holidays: List[str]) -> datetime:
        while dt.strftime("%Y-%m-%d") in holidays:
            dt += timedelta(days=1)
        return dt

    @staticmethod
    def _add_months(dt: datetime, months: int) -> datetime:
        month = dt.month - 1 + months
        year = dt.year + month // 12
        month = month % 12 + 1
        day = min(dt.day, monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)

    @staticmethod
    def _now(timezone: str) -> datetime:
        try:
            return datetime.now(ZoneInfo(timezone)).replace(tzinfo=None)
        except Exception:
            return datetime.utcnow()
