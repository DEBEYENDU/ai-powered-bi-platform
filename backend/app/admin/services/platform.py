"""Platform facade: single composition root for the admin module.

Owns one instance of every sub-service so routers stay thin and tests can
substitute fakes. ``overview`` powers the admin dashboard landing page.
"""

from __future__ import annotations

from typing import Any, Dict

from app.admin.services.alerts import AlertService
from app.admin.services.audit import AuditService
from app.admin.services.feature_flags import FeatureFlagService
from app.admin.services.health import HealthService
from app.admin.services.jobs import JobMonitor
from app.admin.services.metrics import MetricsCollector
from app.admin.services.notifications import NotificationService
from app.admin.services.organizations import OrganizationAdminService
from app.admin.services.rbac import RBACService
from app.admin.services.settings import SettingsService
from app.admin.services.tracing import Tracer
from app.admin.services.users import UserAdminService


class PlatformAdmin:
    def __init__(self) -> None:
        self.audit = AuditService()
        self.rbac = RBACService()
        self.flags = FeatureFlagService()
        self.settings = SettingsService()
        self.health = HealthService()
        self.metrics = MetricsCollector()
        self.tracer = Tracer()
        self.alerts = AlertService(notify=self._on_incident)
        self.jobs = JobMonitor()
        self.notifications = NotificationService()
        self.users = UserAdminService()
        self.orgs = OrganizationAdminService()

    def _on_incident(self, incident: Dict[str, Any]) -> None:
        self.notifications.notify_alert(incident)
        self.audit.append("alert_fired", resource_type="alert",
                          resource_id=incident.get("id", ""),
                          details={"metric": incident.get("metric"),
                                   "value": incident.get("observed_value")})

    def overview(self) -> Dict[str, Any]:
        firing = self.alerts.incidents(status="firing")
        return {
            "health": self.health.check_all()["overall"],
            "organizations": len(self.orgs.list()),
            "users": len(self.users.list(include_inactive=True)),
            "firing_alerts": len(firing),
            "feature_flags": len(self.flags.list()),
            "maintenance": self.settings.maintenance_status(),
            "system": self.metrics.system_snapshot(),
        }


_platform: PlatformAdmin | None = None


def get_platform() -> PlatformAdmin:
    global _platform
    if _platform is None:
        _platform = PlatformAdmin()
    return _platform
