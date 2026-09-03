"""Enterprise Administration, Monitoring & Platform Management (Phase 15).

Packages:
- users/organizations: lifecycle admin around IAM (no auth duplication)
- roles/permissions: RBAC service (system/org/custom roles, simulator)
- settings: validated system settings
- feature_flags: boolean/percentage/org/user/env/scheduled rollouts, kill switches
- monitoring/metrics: collector + Prometheus exposition + platform snapshots
- logging: structured JSON via app.core.logging (reused)
- tracing: correlation IDs + spans (OTel-compatible shape, stdlib)
- alerts: threshold rules, incidents, auto-resolve, notify fan-out
- notifications: in-app notices (email/SMS is a future phase)
- audit: append-only hash-chained log with tamper verification
- health: per-engine aggregate checks
- jobs: Celery inspect monitoring with graceful fallback
- ai/ml/analytics/dashboards/reports: reuse markers (status via existing services)
- scheduler: report-schedule visibility (engine lives in reports/)
- repositories/services/routers/schemas: persistence-agnostic store, facade, API
- middleware: maintenance-mode enforcement
- cache/events/utils: TTL cache, bus, helpers
"""

from app.admin.services.platform import PlatformAdmin, get_platform

__all__ = ["PlatformAdmin", "get_platform"]
