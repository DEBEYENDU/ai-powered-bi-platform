"""Rollback service — safe model version rollback."""

from __future__ import annotations

import contextlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.mlops.models.model import MLOpsDeployment, MLOpsModel, MLOpsModelVersion

log = get_logger("mlops.rollback")


class RollbackService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def rollback(
        self, model_id: str, organization_id: str, target_version_id: str
    ) -> dict[str, Any]:
        model = self.db.scalars(
            select(MLOpsModel).where(
                MLOpsModel.id == model_id,
                MLOpsModel.organization_id == organization_id,
                MLOpsModel.deleted_at.is_(None),
            )
        ).first()
        if not model:
            raise ValueError(f"Model {model_id} not found")

        target_version = self.db.scalars(
            select(MLOpsModelVersion).where(
                MLOpsModelVersion.id == target_version_id,
                MLOpsModelVersion.organization_id == organization_id,
            )
        ).first()
        if not target_version:
            raise ValueError(f"Target version {target_version_id} not found")

        if target_version.model_id != model_id:
            raise ValueError("Target version does not belong to this model")

        current_dep = self.db.scalars(
            select(MLOpsDeployment).where(
                MLOpsDeployment.model_id == model_id,
                MLOpsDeployment.environment == "production",
                MLOpsDeployment.status == "active",
                MLOpsDeployment.organization_id == organization_id,
            )
        ).first()

        if current_dep:
            current_dep.status = "rolled_back"
            current_dep.stopped_at = __import__("datetime").datetime.utcnow()

        new_dep = MLOpsDeployment(
            model_id=model_id,
            model_version_id=target_version_id,
            organization_id=organization_id,
            environment="production",
            config=current_dep.config if current_dep else {},
            deployed_by=current_dep.deployed_by if current_dep else "",
        )
        self.db.add(new_dep)

        for v in self.db.scalars(
            select(MLOpsModelVersion).where(
                MLOpsModelVersion.model_id == model_id,
                MLOpsModelVersion.organization_id == organization_id,
            )
        ).all():
            v.is_active = v.id == target_version_id

        self.db.commit()
        self.db.refresh(new_dep)

        self._audit(
            "model_rollback", model_id, organization_id, {"target_version": target_version.version}
        )
        self._metrics("mlops_rollbacks_total", 1.0)
        log.info("rollback_completed", model_id=model_id, target_version=target_version.version)

        return {
            "success": True,
            "model_id": model_id,
            "previous_version": current_dep.model_version_id if current_dep else None,
            "new_version": target_version.version,
            "deployment_id": new_dep.id,
        }

    def _audit(self, action: str, resource_id: str, org_id: str, details: dict) -> None:
        with contextlib.suppress(Exception):
            from app.admin.services.platform import PlatformAdmin

            platform = PlatformAdmin()
            platform.audit.append(
                action=action,
                resource_type="mlops_rollback",
                resource_id=resource_id,
                organization_id=org_id,
                details=details,
            )

    def _metrics(self, name: str, value: float, **labels: str) -> None:
        with contextlib.suppress(Exception):
            from app.admin.services.platform import PlatformAdmin

            platform = PlatformAdmin()
            platform.metrics.record(name, value, labels=labels or None)
