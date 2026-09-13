"""Tests for the dashboards module (skipped when no database is available)."""

import pytest


def _require_db():
    from app.admin.repositories.db_store import db_available

    if not db_available():
        pytest.skip("database unavailable")


def test_crud_roundtrip():
    _require_db()
    from app.dashboards import service

    created = service.create_dashboard(
        {
            "name": "Test Exec",
            "organization_id": "",
            "widgets": [{"widget_id": "w1", "kind": "kpi", "title": "Rev"}],
        }
    )
    try:
        assert created["widget_count"] == 1
        fetched = service.get_dashboard(created["id"])
        assert fetched is not None and fetched["name"] == "Test Exec"
        updated = service.update_dashboard(created["id"], {"name": "Test Exec 2"})
        assert updated is not None and updated["name"] == "Test Exec 2"
        listed = service.list_dashboards()
        assert any(d["id"] == created["id"] for d in listed)
    finally:
        assert service.delete_dashboard(created["id"]) is True
        assert service.get_dashboard(created["id"]) is None


def test_widget_validation():
    _require_db()
    from app.dashboards import service

    with pytest.raises(ValueError):
        service.create_dashboard({"name": "Bad", "widgets": [{"widget_id": "w1", "kind": "nope"}]})
    with pytest.raises(ValueError):
        service.create_dashboard(
            {
                "name": "Dup",
                "widgets": [
                    {"widget_id": "w1", "kind": "kpi"},
                    {"widget_id": "w1", "kind": "kpi"},
                ],
            }
        )


def test_archive_restore():
    _require_db()
    from app.dashboards import service

    created = service.create_dashboard({"name": "Arch Me"})
    try:
        assert service.archive_dashboard(created["id"], True)["archived"] is True
        assert service.get_dashboard(created["id"]) is None
        assert service.archive_dashboard(created["id"], False)["archived"] is False
        assert service.get_dashboard(created["id"]) is not None
    finally:
        service.delete_dashboard(created["id"])
