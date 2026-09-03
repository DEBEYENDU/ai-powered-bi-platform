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


class TestAudit:
    def test_append_query_verify(self):
        audit = AuditService()
        audit.append("user_created", "user", "u1", actor_id="admin")
        audit.append("user_suspended", "user", "u1", actor_id="admin")
        assert len(audit.query()) == 2
        assert audit.query(action="user_created")
        assert audit.verify_chain()["valid"] is True

    def test_chain_detects_tampering(self):
        audit = AuditService()
        audit.append("x", "r", "1")
        audit._entries[0]["details"] = {"tampered": True}
        assert audit.verify_chain()["valid"] is False


class TestRBAC:
    def test_seed_check_simulate(self):
        rbac = RBACService()
        rbac.assign_role("u1", "sys-viewer")
        assert rbac.check("u1", "datasets:read") is True
        assert rbac.check("u1", "admin:settings") is False
        sim = rbac.simulate("u1")
        assert "datasets:read" in sim["permissions"]

    def test_custom_role(self):
        rbac = RBACService()
        role = rbac.create_role("data-steward", permission_codes=["datasets:write"])
        rbac.assign_role("u2", role["id"])
        assert rbac.check("u2", "datasets:write") is True
        assert rbac.unassign_role("u2", role["id"]) is True
        assert rbac.check("u2", "datasets:write") is False

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
        flags.create("org-feat", rules=[{"name": "o1", "organizations": ["o1"],
                                         "enabled": True}])
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
        users = UserAdminService()
        user = users.create("a@x.com", "password123")
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
        orgs = OrganizationAdminService()
        org = orgs.create("Acme")
        assert orgs.quotas(org["id"])["storage_mb"] == 10240
        assert orgs.update_quotas(org["id"], {"storage_mb": 512})["storage_mb"] == 512
        with pytest.raises(ValueError):
            orgs.update_quotas(org["id"], {"storage_mb": -1})


class TestPlatform:
    def test_overview_shape(self):
        overview = PlatformAdmin().overview()
        for key in ("health", "organizations", "users", "firing_alerts",
                    "feature_flags", "maintenance", "system"):
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
