"""Admin event bus (re-uses the reports event shape)."""

from __future__ import annotations

from app.reports.events.events import EventBus as _ReportsBus  # type: ignore


class AdminEventBus(_ReportsBus):
    """Same subscribe/publish/history API, namespaced for admin events."""


_bus: AdminEventBus | None = None


def get_bus() -> AdminEventBus:
    global _bus
    if _bus is None:
        _bus = AdminEventBus()
    return _bus
