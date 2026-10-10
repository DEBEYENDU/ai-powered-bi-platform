"""Shared fixtures for admin tests.

Maintenance-mode tests build their own ``SettingsService`` and persist the
mode to the database. Without restoration the dev database is left in
``readonly`` after ``pytest`` and the app boots read-only — so every test
puts the platform back and we verify it actually stuck.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def restore_maintenance_mode():
    yield
    try:
        from app.admin.repositories import db_store
        from app.admin.services.platform import get_platform

        # Always write: tests use their own SettingsService instances, so the
        # singleton's in-memory mode tells us nothing about the database.
        get_platform().settings.set_maintenance("off", "")
        latest = db_store.maintenance_latest()
        if latest and latest.get("mode") != "off":
            raise RuntimeError(f"maintenance mode not restored in db: {latest}")
    except Exception as exc:  # visible failure beats a silently read-only dev db
        print(f"WARNING: could not restore maintenance mode: {exc}", flush=True)


@pytest.fixture(scope="session", autouse=True)
def report_final_maintenance_mode():
    yield
    try:
        from app.admin.repositories import db_store

        latest = db_store.maintenance_latest()
        if latest and latest.get("mode") != "off":
            print(f"\nFINAL maintenance mode: {latest}", flush=True)
    except Exception:
        pass
