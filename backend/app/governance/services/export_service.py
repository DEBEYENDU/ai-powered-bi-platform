"""Export security service — controls data export based on classification and permissions."""

from __future__ import annotations

import contextlib
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.governance.services.classification_service import ClassificationService

log = get_logger("governance.export")


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def validate_export(
        self,
        user_id: str,
        organization_id: str,
        resource_type: str,
        resource_id: str,
        export_format: str = "csv",
    ) -> dict[str, Any]:
        from app.admin.services.rbac import RBACService

        rbac = RBACService()

        if not rbac.check(user_id, f"{resource_type}.export"):
            return {"allowed": False, "reason": f"Missing {resource_type}.export permission"}

        classification_svc = ClassificationService(self.db)
        allowed, reason = classification_svc.can_export(resource_type, resource_id, organization_id)
        if not allowed:
            return {"allowed": False, "reason": reason}

        return {"allowed": True, "reason": ""}

    def record_export(
        self,
        user_id: str,
        organization_id: str,
        resource_type: str,
        resource_id: str,
        export_format: str,
        record_count: int = 0,
    ) -> None:
        with contextlib.suppress(Exception):
            from app.governance.models.policy import SecurityEvent

            event = SecurityEvent(
                organization_id=organization_id,
                event_type="data_export",
                severity="INFO",
                actor_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action="export",
                outcome="allowed",
                details={"format": export_format, "record_count": record_count},
            )
            self.db.add(event)
            self.db.commit()
