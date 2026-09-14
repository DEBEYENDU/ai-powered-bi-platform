"""Tests for the Admin Platform (stdlib only, no broker/db needed)."""

import pytest

from app.admin.services.alerts import AlertService
from app.admin.services.audit import AuditService
from app.admin.services.feature_flags import FeatureFlagService
from app.admin.services.health import HealthService
from app.admin.services.jobs import JobMonitor
from app.admin.services.metrics import MetricsCollector
from app.admin.services.notifications import NotificationService
from app.admin.services.organizations import OrganizationAdminService
from app.admin.services.platform import PlatformAdmin
from app.admin.services.rbac import RBACService
from app.admin.services.settings import SettingsService
from app.admin.services.tracing import Tracer
from app.admin.services.users import UserAdminService


class TestMaintenanceEscapeHatch:
    """Regression tests for the readonly deadlock: the maintenance-management
    endpoints must stay reachable in every mode, or the platform can never
    leave readonly/maintenance via the API."""

    def _middleware(self, mode: str):
        from app.admin.middleware.maintenance import MaintenanceMiddleware

        settings = SettingsService()
        settings.set_maintenance(mode, "test")
        return MaintenanceMiddleware(app=None, settings_service=settings)

    def _request(self, method: str, path: str):
        from starlette.requests import Request

        return Request(
            {
                "type": "http",
                "method": method,
                "path": path,
                "headers": [],
                "query_string": b"",
            }
        )

    async def _dispatch(self, middleware, method: str, path: str) -> int:
        from starlette.responses import PlainTextResponse

        async def call_next(request):
            return PlainTextResponse("ok")

        response = await middleware.dispatch(self._request(method, path), call_next)
        return response.status_code

    def test_escape_hatch_in_readonly(self):
        import asyncio

        middleware = self._middleware("readonly")
        # The escape hatch itself must stay open ...
        assert asyncio.run(self._dispatch(middleware, "POST", "/admin/maintenance")) == 200
        assert asyncio.run(self._dispatch(middleware, "POST", "/api/v1/admin/maintenance")) == 200
        # ... while ordinary writes stay blocked and reads pass.
        assert asyncio.run(self._dispatch(middleware, "POST", "/admin/users")) == 503
        assert asyncio.run(self._dispatch(middleware, "GET", "/admin/users")) == 200

    def test_maintenance_mode_blocks_reads_but_not_health_or_docs(self):
        import asyncio

        middleware = self._middleware("maintenance")
        assert asyncio.run(self._dispatch(middleware, "GET", "/admin/users")) == 503
        assert asyncio.run(self._dispatch(middleware, "GET", "/health")) == 200
        assert asyncio.run(self._dispatch(middleware, "GET", "/docs")) == 200
        assert asyncio.run(self._dispatch(middleware, "POST", "/admin/maintenance")) == 200

    def test_off_allows_everything(self):
        import asyncio

        middleware = self._middleware("off")
        assert asyncio.run(self._dispatch(middleware, "POST", "/admin/users")) == 200
        assert asyncio.run(self._dispatch(middleware, "DELETE", "/admin/users/1")) == 200

    def test_mode_change_is_visible(self):
        settings = SettingsService()
        assert settings.maintenance_status()["mode"] == "off"
        settings.set_maintenance("readonly", "test")
        assert settings.maintenance_status()["mode"] == "readonly"
        settings.set_maintenance("off", "")
        assert settings.maintenance_status()["mode"] == "off"

    def test_singleton_is_single(self):
        from app.admin.services.platform import get_platform

        first = get_platform()
        second = get_platform()
        assert first is second
        assert first.settings is second.settings


class TestMaintenanceModeMatrix:
    """Comprehensive tests covering every combination of maintenance mode x HTTP method.

    Matrix:
    1. OFF + GET -> allowed
    2. OFF + POST -> allowed
    3. OFF + PUT -> allowed
    4. OFF + PATCH -> allowed
    5. OFF + DELETE -> allowed

    6. READONLY + GET -> allowed
    7. READONLY + HEAD -> allowed
    8. READONLY + OPTIONS -> allowed
    9. READONLY + POST -> 503
    10. READONLY + PUT -> 503
    11. READONLY + PATCH -> 503
    12. READONLY + DELETE -> 503

    13. MAINTENANCE + GET -> 503
    14. MAINTENANCE + POST -> 503
    15. MAINTENANCE + PUT -> 503
    16. MAINTENANCE + DELETE -> 503

    Escape hatches:
    17. MAINTENANCE + /health -> allowed
    18. MAINTENANCE + /docs -> allowed
    19. MAINTENANCE + /admin/maintenance -> allowed
    20. MAINTENANCE + override-token -> allowed
    21. READONLY + override-token -> allowed
    """

    def _middleware(self, mode: str):
        from app.admin.middleware.maintenance import MaintenanceMiddleware

        settings = SettingsService()
        settings.set_maintenance(mode, "test")
        return MaintenanceMiddleware(app=None, settings_service=settings)

    def _request(self, method: str, path: str, headers: list[tuple[bytes, bytes]] | None = None):
        from starlette.requests import Request

        return Request(
            {
                "type": "http",
                "method": method,
                "path": path,
                "headers": headers or [],
                "query_string": b"",
            }
        )

    async def _dispatch(self, middleware, method: str, path: str, headers=None) -> int:
        from starlette.responses import PlainTextResponse

        async def call_next(request):
            return PlainTextResponse("ok")

        response = await middleware.dispatch(self._request(method, path, headers), call_next)
        return response.status_code

    # OFF mode
    def test_off_get(self):
        import asyncio

        assert asyncio.run(self._dispatch(self._middleware("off"), "GET", "/admin/users")) == 200

    def test_off_post(self):
        import asyncio

        assert asyncio.run(self._dispatch(self._middleware("off"), "POST", "/admin/users")) == 200

    def test_off_put(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("off"), "PUT", "/admin/settings/x")) == 200
        )

    def test_off_patch(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("off"), "PATCH", "/admin/settings/x"))
            == 200
        )

    def test_off_delete(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("off"), "DELETE", "/admin/users/1")) == 200
        )

    # READONLY mode
    def test_readonly_get(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("readonly"), "GET", "/admin/users")) == 200
        )

    def test_readonly_head(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("readonly"), "HEAD", "/admin/users")) == 200
        )

    def test_readonly_options(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("readonly"), "OPTIONS", "/admin/users"))
            == 200
        )

    def test_readonly_post(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("readonly"), "POST", "/admin/users")) == 503
        )

    def test_readonly_put(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("readonly"), "PUT", "/admin/settings/x"))
            == 503
        )

    def test_readonly_patch(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("readonly"), "PATCH", "/admin/settings/x"))
            == 503
        )

    def test_readonly_delete(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("readonly"), "DELETE", "/admin/users/1"))
            == 503
        )

    # MAINTENANCE mode
    def test_maintenance_get(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("maintenance"), "GET", "/admin/users"))
            == 503
        )

    def test_maintenance_post(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("maintenance"), "POST", "/admin/users"))
            == 503
        )

    def test_maintenance_put(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("maintenance"), "PUT", "/admin/settings/x"))
            == 503
        )

    def test_maintenance_delete(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("maintenance"), "DELETE", "/admin/users/1"))
            == 503
        )

    # Escape hatches
    def test_maintenance_health_allowed(self):
        import asyncio

        assert asyncio.run(self._dispatch(self._middleware("maintenance"), "GET", "/health")) == 200

    def test_maintenance_docs_allowed(self):
        import asyncio

        assert asyncio.run(self._dispatch(self._middleware("maintenance"), "GET", "/docs")) == 200

    def test_maintenance_redoc_allowed(self):
        import asyncio

        assert asyncio.run(self._dispatch(self._middleware("maintenance"), "GET", "/redoc")) == 200

    def test_maintenance_openapi_allowed(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("maintenance"), "GET", "/openapi.json"))
            == 200
        )

    def test_maintenance_endpoint_allowed(self):
        import asyncio

        assert (
            asyncio.run(
                self._dispatch(self._middleware("maintenance"), "POST", "/admin/maintenance")
            )
            == 200
        )
        assert (
            asyncio.run(
                self._dispatch(self._middleware("maintenance"), "GET", "/admin/maintenance")
            )
            == 200
        )
        assert (
            asyncio.run(
                self._dispatch(self._middleware("maintenance"), "POST", "/api/v1/admin/maintenance")
            )
            == 200
        )

    def test_readonly_maintenance_endpoint_allowed(self):
        import asyncio

        assert (
            asyncio.run(self._dispatch(self._middleware("readonly"), "POST", "/admin/maintenance"))
            == 200
        )

    # Override token
    def test_override_token_bypasses_maintenance(self):
        import asyncio

        from app.admin.middleware.maintenance import MaintenanceMiddleware

        settings = SettingsService()
        settings.set_maintenance("maintenance", "test")
        token = settings.mint_override_token("admin")
        middleware = MaintenanceMiddleware(app=None, settings_service=settings)

        assert (
            asyncio.run(
                self._dispatch(
                    middleware, "GET", "/admin/users", [(b"x-admin-override", token.encode())]
                )
            )
            == 200
        )
        assert (
            asyncio.run(
                self._dispatch(
                    middleware, "POST", "/admin/users", [(b"x-admin-override", token.encode())]
                )
            )
            == 200
        )

    def test_override_token_bypasses_readonly(self):
        import asyncio

        from app.admin.middleware.maintenance import MaintenanceMiddleware

        settings = SettingsService()
        settings.set_maintenance("readonly", "test")
        token = settings.mint_override_token("admin")
        middleware = MaintenanceMiddleware(app=None, settings_service=settings)

        assert (
            asyncio.run(
                self._dispatch(
                    middleware, "POST", "/admin/users", [(b"x-admin-override", token.encode())]
                )
            )
            == 200
        )

    def test_invalid_override_token_blocked(self):
        import asyncio

        from app.admin.middleware.maintenance import MaintenanceMiddleware

        settings = SettingsService()
        settings.set_maintenance("maintenance", "test")
        middleware = MaintenanceMiddleware(app=None, settings_service=settings)

        assert (
            asyncio.run(
                self._dispatch(
                    middleware, "POST", "/admin/users", [(b"x-admin-override", b"bogus-token")]
                )
            )
            == 503
        )


class TestMaintenanceStatusResponse:
    """Verify maintenance_status() returns correct shape and is_write_blocked flag."""

    def _fresh_settings(self, mode: str = "off"):
        s = SettingsService()
        # Prevent DB hydration in unit tests: mark as loaded so
        # maintenance_status() returns the in-memory state only.
        s._maintenance_loaded = True
        if mode != "off":
            s.set_maintenance(mode, "test")
        return s

    def test_off_returns_write_not_blocked(self):
        settings = self._fresh_settings("off")
        status = settings.maintenance_status()
        assert status["mode"] == "off"
        assert status["is_write_blocked"] is False

    def test_readonly_returns_write_blocked(self):
        settings = self._fresh_settings("readonly")
        status = settings.maintenance_status()
        assert status["mode"] == "readonly"
        assert status["is_write_blocked"] is True

    def test_maintenance_returns_write_blocked(self):
        settings = self._fresh_settings("maintenance")
        status = settings.maintenance_status()
        assert status["mode"] == "maintenance"
        assert status["is_write_blocked"] is True

    def test_status_contains_expected_keys(self):
        settings = self._fresh_settings()
        status = settings.maintenance_status()
        for key in ("mode", "message", "starts_at", "ends_at", "is_write_blocked"):
            assert key in status

    def test_roundtrip_mode_change(self):
        settings = self._fresh_settings()
        settings.set_maintenance("readonly", "test")
        assert settings.maintenance_status()["mode"] == "readonly"
        settings.set_maintenance("off", "")
        assert settings.maintenance_status()["mode"] == "off"
        assert settings.maintenance_status()["is_write_blocked"] is False


class TestMaintenanceAPIResponse:
    """Verify the 503 response body includes mode and hint fields."""

    def _middleware_for(self, mode: str):
        from app.admin.middleware.maintenance import MaintenanceMiddleware

        s = SettingsService()
        s._maintenance_loaded = True
        s.set_maintenance(mode, "")
        return MaintenanceMiddleware(app=None, settings_service=s)

    def test_readonly_503_includes_mode_and_hint(self):
        import asyncio

        middleware = self._middleware_for("readonly")

        async def _run():
            from starlette.requests import Request

            async def call_next(request):
                from starlette.responses import PlainTextResponse

                return PlainTextResponse("ok")

            req = Request(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/admin/users",
                    "headers": [],
                    "query_string": b"",
                }
            )
            resp = await middleware.dispatch(req, call_next)
            return resp

        resp = asyncio.run(_run())
        assert resp.status_code == 503
        import json

        body = json.loads(resp.body)
        assert body["mode"] == "readonly"
        assert "hint" in body
        assert "off" in body["hint"]

    def test_maintenance_503_includes_mode_and_hint(self):
        import asyncio

        middleware = self._middleware_for("maintenance")

        async def _run():
            from starlette.requests import Request

            async def call_next(request):
                from starlette.responses import PlainTextResponse

                return PlainTextResponse("ok")

            req = Request(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/admin/users",
                    "headers": [],
                    "query_string": b"",
                }
            )
            resp = await middleware.dispatch(req, call_next)
            return resp

        resp = asyncio.run(_run())
        assert resp.status_code == 503
        import json

        body = json.loads(resp.body)
        assert body["mode"] == "maintenance"
        assert "hint" in body

    def test_off_no_503(self):
        import asyncio

        middleware = self._middleware_for("off")

        async def _run():
            from starlette.requests import Request

            async def call_next(request):
                from starlette.responses import PlainTextResponse

                return PlainTextResponse("ok")

            req = Request(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/admin/users",
                    "headers": [],
                    "query_string": b"",
                }
            )
            resp = await middleware.dispatch(req, call_next)
            return resp

        resp = asyncio.run(_run())
        assert resp.status_code == 200


class TestAudit:
    def test_append_query_verify(self):
        audit = AuditService()
        first = audit.append("user_created", "user", "u1", actor_id="admin")
        second = audit.append("user_suspended", "user", "u1", actor_id="admin")
        ids = {e["id"] for e in audit.query(actor_id="admin", limit=1000)}
        assert first["id"] in ids and second["id"] in ids
        assert audit.query(action="user_created")
        assert audit.verify_chain()["valid"] is True

    def test_chain_detects_tampering(self):
        from unittest import mock

        audit = AuditService()
        with (
            mock.patch("app.admin.repositories.db_store.audit_query_db", return_value=[]),
            mock.patch("app.admin.repositories.db_store.audit_insert", return_value=True),
        ):
            audit.append("x", "r", "1")
            assert audit.verify_chain()["valid"] is True
            audit._entries[0]["details"] = {"tampered": True}
            result = audit.verify_chain()
            assert result["valid"] is False
            assert result["broken_at_index"] == 0


class TestRBAC:
    def test_seed_check_simulate(self):
        rbac = RBACService()
        rbac.assign_role("u1", "sys-viewer")
        assert rbac.check("u1", "datasets:read") is True
        assert rbac.check("u1", "datasets.view") is True
        assert rbac.check("u1", "settings.view") is True
        assert rbac.check("u1", "settings.update") is False
        sim = rbac.simulate("u1")
        assert "datasets.view" in sim["permissions"]

    def test_custom_role(self):
        rbac = RBACService()
        role = rbac.create_role("data-steward", permission_codes=["datasets:write"])
        # Legacy code expands to canonical grants.
        assert rbac.check("u2", "datasets.create") is False
        rbac.assign_role("u2", role["id"])
        assert rbac.check("u2", "datasets:write") is True
        assert rbac.check("u2", "datasets.create") is True
        assert rbac.check("u2", "datasets.delete") is False
        assert rbac.unassign_role("u2", role["id"]) is True
        assert rbac.check("u2", "datasets:write") is False

    def test_role_edit_clone_delete(self):
        rbac = RBACService()
        role = rbac.create_role("ops", permission_codes=["alerts.view"])
        updated = rbac.update_role(role["id"], {"description": "Ops team"})
        assert updated is not None and updated["description"] == "Ops team"
        clone = rbac.clone_role(role["id"], "ops-copy")
        assert clone["name"] == "ops-copy"
        assert rbac.check("u9", "alerts.view") is False
        rbac.assign_role("u9", clone["id"])
        assert rbac.check("u9", "alerts.view") is True
        assert rbac.role_users(clone["id"]) == ["u9"]
        assert rbac.delete_role(clone["id"]) is True
        assert rbac.check("u9", "alerts.view") is False
        with pytest.raises(ValueError):
            rbac.delete_role("sys-viewer")

    def test_unknown_permission_rejected(self):
        rbac = RBACService()
        with pytest.raises(ValueError):
            rbac.create_role("bad", permission_codes=["nope:nah"])


class TestFlags:
    def test_percentage_rollout_stable(self):
        flags = FeatureFlagService()
        flags.create("new-ui", rules=[{"name": "pct", "percentage": 50}])
        first = flags.evaluate("new-ui", user_id="alice")["enabled"]
        assert flags.evaluate("new-ui", user_id="alice")["enabled"] == first

    def test_kill_switch(self):
        flags = FeatureFlagService()
        flags.create("beta", default_value={"enabled": True})
        assert flags.evaluate("beta")["enabled"] is True
        flags.kill("beta")
        assert flags.evaluate("beta")["enabled"] is False

    def test_org_targeting(self):
        flags = FeatureFlagService()
        flags.create("org-feat", rules=[{"name": "o1", "organizations": ["o1"], "enabled": True}])
        assert flags.evaluate("org-feat", organization_id="o1")["enabled"] is True
        assert flags.evaluate("org-feat", organization_id="o2")["enabled"] is False


class TestSettings:
    def test_validation(self):
        settings = SettingsService()
        settings.update("log_level", "DEBUG")
        with pytest.raises(ValueError):
            settings.update("log_level", "VERBOSE")
        with pytest.raises(ValueError):
            settings.update("nope", 1)

    def test_maintenance_override(self):
        settings = SettingsService()
        settings.set_maintenance("readonly", "Deploying")
        assert settings.is_write_blocked() is True
        token = settings.mint_override_token("admin")
        assert settings.check_override(token) is True
        assert settings.check_override("bogus") is False


class TestHealthMetrics:
    def test_check_all_shape(self):
        health = HealthService()
        result = health.check_all()
        assert result["overall"] in ("ok", "degraded", "down")
        assert any(s["service"] == "database" for s in result["services"])

    def test_prometheus_exposition(self):
        metrics = MetricsCollector()
        metrics.record("api_latency_ms", 42.0, labels={"route": "/x"})
        out = metrics.render_prometheus()
        assert "bi_api_latency_ms" in out and "42.0" in out

    def test_request_recording_drives_snapshot(self):
        metrics = MetricsCollector()
        for _ in range(5):
            metrics.record_request(100.0, 200, "/x")
        metrics.record_request(500.0, 500, "/x")
        snapshot = metrics.system_snapshot()
        assert snapshot["api_requests_total"] == 6
        assert snapshot["api_errors_total"] == 1
        assert snapshot["api_throughput_rpm"] == 6.0
        assert snapshot["api_latency_ms"] > 0
        assert snapshot["api_latency_p95_ms"] >= snapshot["api_latency_ms"]
        assert "bi_request_duration_ms_count 6" in metrics.render_prometheus()

    def test_queue_not_configured_without_broker(self):
        stats = MetricsCollector.queue_stats()
        assert stats["queue_length"] == "Not Configured" or isinstance(
            stats["queue_length"], (int, float)
        )

    def test_storage_health_details(self):
        health = HealthService()
        result = health.check_all()
        storage = next(s for s in result["services"] if s["service"] == "storage")
        assert "directory" in storage
        assert "readable" in storage
        assert "writable" in storage


class TestStoragePaths:
    def test_settings_defaults_are_backend_local(self):
        from pathlib import Path

        from app.core.config import BASE_DIR, get_settings

        get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None
        settings = get_settings()
        assert Path(settings.storage_path).is_absolute()
        assert "\\tmp" not in settings.storage_path.replace("/", "\\")
        assert str(BASE_DIR) in settings.storage_path or "storage" in settings.storage_path

    def test_env_file_location_is_absolute(self):
        from app.core.config import ENV_FILE

        assert ENV_FILE.is_absolute()
        assert ENV_FILE.name == ".env"

    def test_provider_roundtrip(self):
        import asyncio
        import tempfile
        from pathlib import Path

        from app.dataset.storage.base import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmp:
            provider = LocalStorageProvider(base_path=Path(tmp))
            asyncio.run(provider.put("a/b.bin", b"data"))
            assert asyncio.run(provider.exists("a/b.bin")) is True
            assert asyncio.run(provider.get("a/b.bin")) == b"data"

    def test_provider_blocks_escape(self):
        import asyncio
        import tempfile
        from pathlib import Path

        import pytest

        from app.dataset.storage.base import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmp:
            provider = LocalStorageProvider(base_path=Path(tmp))
            with pytest.raises(ValueError):
                asyncio.run(provider.put("../evil.bin", b"x"))

    def test_cache_hit_rate(self):
        from app.cache.service import CacheService

        before_hits, before_misses = CacheService.total_hits(), CacheService.total_misses()
        cache = CacheService(namespace="test-rate")
        cache.set("k", "v")
        assert cache.get("k") == "v"
        assert cache.get("absent") is None
        assert CacheService.total_hits() == before_hits + 1
        assert CacheService.total_misses() == before_misses + 1
        assert 0.0 <= CacheService.hit_rate() <= 1.0

    def test_system_snapshot(self):
        snapshot = MetricsCollector().system_snapshot()
        assert "uptime_seconds" in snapshot


class TestTracing:
    def test_span_nesting(self):
        tracer = Tracer()
        tracer.start_trace("root")
        with tracer.trace("child"):
            pass
        assert len(tracer.recent()) >= 1
        trace_id = tracer.recent()[-1]["trace_id"]
        assert tracer.spans_for_trace(trace_id)


class TestAlerts:
    def test_fire_ack_resolve(self):
        alerts = AlertService()
        rule = alerts.create_rule("cpu high", "cpu_percent", 90.0)
        assert rule["metric"] == "cpu_percent"
        fired = alerts.evaluate("cpu_percent", 95.0)
        assert len(fired) == 1
        # second breach while firing does not duplicate
        assert len(alerts.evaluate("cpu_percent", 96.0)) == 1
        assert len(alerts.incidents(status="firing")) == 1
        alerts.acknowledge(fired[0]["id"])
        assert alerts.incidents(status="acknowledged")
        alerts.evaluate("cpu_percent", 10.0)
        assert alerts.incidents(status="resolved")

    def test_bad_operator(self):
        with pytest.raises(ValueError):
            AlertService().create_rule("x", "m", 1.0, rule_operator="~")


class TestUsersOrgs:
    def test_user_lifecycle(self):
        import uuid

        users = UserAdminService()
        uid = uuid.uuid4().hex[:8]
        user = users.create(f"a-{uid}@x.com", "password123")
        assert users.suspend(user["id"])["suspended"] is True
        assert users.reset_password(user["id"], "newpassword123") is True
        assert users.restore(user["id"])["is_active"] is True
        session = users.create_session(user["id"])
        assert users.revoke_session(session["id"]) is True
        key = users.create_api_key(user["id"])
        assert key["api_key"] and users.revoke_api_key(key["id"]) is True
        users.record_login(user["id"], True)
        assert users.login_history(user["id"])

    def test_org_quotas(self):
        import uuid

        orgs = OrganizationAdminService()
        org = orgs.create(f"Acme-{uuid.uuid4().hex[:8]}")
        assert orgs.quotas(org["id"])["storage_mb"] == 10240
        assert orgs.update_quotas(org["id"], {"storage_mb": 512})["storage_mb"] == 512
        with pytest.raises(ValueError):
            orgs.update_quotas(org["id"], {"storage_mb": -1})


class TestPlatform:
    def test_overview_shape(self):
        overview = PlatformAdmin().overview()
        for key in (
            "health",
            "organizations",
            "users",
            "firing_alerts",
            "feature_flags",
            "maintenance",
            "system",
        ):
            assert key in overview

    def test_jobs_degrade_cleanly(self):
        status = JobMonitor().status()
        assert "broker" in status and "workers" in status

    def test_notifications(self):
        svc = NotificationService()
        item = svc.create("u1", "Hello")
        assert svc.unread_count("u1") == 1
        svc.mark_read(item["id"])
        assert svc.unread_count("u1") == 0
