"""Deployment management service."""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.mlops.engine.lifecycle import validate_deployment_transition
from app.mlops.models.model import MLOpsDeployment, MLOpsModel, MLOpsModelVersion

log = get_logger("mlops.deployment")


class DeploymentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_deployment(
        self, data: dict[str, Any], organization_id: str, deployed_by: str = ""
    ) -> MLOpsDeployment:
        deployment = MLOpsDeployment(
            model_id=data["model_id"],
            model_version_id=data["model_version_id"],
            organization_id=organization_id,
            environment=data.get("environment", "staging"),
            config=data.get("config", {}),
            deployed_by=deployed_by,
        )
        self.db.add(deployment)

        version = self.db.scalars(
            select(MLOpsModelVersion).where(MLOpsModelVersion.id == data["model_version_id"])
        ).first()
        if version:
            version.status = "staged" if data.get("environment") == "staging" else version.status

        self.db.commit()
        self.db.refresh(deployment)

        self._audit(
            "deployment_created",
            deployment.id,
            organization_id,
            {"environment": deployment.environment},
        )
        self._metrics("mlops_deployments_total", 1.0)
        log.info("deployment_created", deployment_id=deployment.id)
        return deployment

    def get_deployment(self, deployment_id: str, organization_id: str) -> MLOpsDeployment | None:
        stmt = select(MLOpsDeployment).where(
            MLOpsDeployment.id == deployment_id,
            MLOpsDeployment.organization_id == organization_id,
        )
        return self.db.scalars(stmt).first()

    def get_active_deployment(
        self, model_id: str, organization_id: str, environment: str = "production"
    ) -> MLOpsDeployment | None:
        stmt = select(MLOpsDeployment).where(
            MLOpsDeployment.model_id == model_id,
            MLOpsDeployment.organization_id == organization_id,
            MLOpsDeployment.environment == environment,
            MLOpsDeployment.status == "active",
        )
        return self.db.scalars(stmt).first()

    def list_deployments(
        self, organization_id: str, model_id: str | None = None
    ) -> list[MLOpsDeployment]:
        stmt = select(MLOpsDeployment).where(MLOpsDeployment.organization_id == organization_id)
        if model_id:
            stmt = stmt.where(MLOpsDeployment.model_id == model_id)
        return list(self.db.scalars(stmt.order_by(MLOpsDeployment.deployed_at.desc()).all()))

    def activate_deployment(
        self, deployment_id: str, organization_id: str
    ) -> MLOpsDeployment | None:
        dep = self.get_deployment(deployment_id, organization_id)
        if not dep:
            return None
        validate_deployment_transition(dep.status, "active")
        dep.status = "active"
        dep.health_status = "healthy"
        self.db.commit()
        self.db.refresh(dep)
        self._audit("deployment_activated", deployment_id, organization_id, {})
        return dep

    def stop_deployment(self, deployment_id: str, organization_id: str) -> MLOpsDeployment | None:
        dep = self.get_deployment(deployment_id, organization_id)
        if not dep:
            return None
        validate_deployment_transition(dep.status, "stopped")
        dep.status = "stopped"
        dep.stopped_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(dep)
        self._audit("deployment_stopped", deployment_id, organization_id, {})
        return dep

    def rollback_deployment(
        self, deployment_id: str, organization_id: str, target_version_id: str
    ) -> MLOpsDeployment | None:
        dep = self.get_deployment(deployment_id, organization_id)
        if not dep:
            return None

        target_version = self.db.scalars(
            select(MLOpsModelVersion).where(
                MLOpsModelVersion.id == target_version_id,
                MLOpsModelVersion.organization_id == organization_id,
            )
        ).first()
        if not target_version:
            raise ValueError(f"Target version {target_version_id} not found")

        validate_deployment_transition(dep.status, "rolled_back")
        dep.status = "rolled_back"
        dep.stopped_at = datetime.utcnow()

        new_dep = MLOpsDeployment(
            model_id=dep.model_id,
            model_version_id=target_version_id,
            organization_id=organization_id,
            environment=dep.environment,
            config=dep.config,
            deployed_by=dep.deployed_by,
        )
        self.db.add(new_dep)
        self.db.commit()
        self.db.refresh(new_dep)

        self._audit(
            "deployment_rollback",
            deployment_id,
            organization_id,
            {"target_version": target_version.version},
        )
        self._metrics("mlops_rollbacks_total", 1.0)
        log.info(
            "deployment_rollback",
            deployment_id=deployment_id,
            target_version=target_version.version,
        )
        return new_dep

    def get_health(self, model_id: str, organization_id: str) -> dict[str, Any]:
        dep = self.get_active_deployment(model_id, organization_id)
        self.db.scalars(
            select(MLOpsModel).where(
                MLOpsModel.id == model_id, MLOpsModel.organization_id == organization_id
            )
        ).first()
        version = None
        if dep:
            version = self.db.scalars(
                select(MLOpsModelVersion).where(MLOpsModelVersion.id == dep.model_version_id)
            ).first()

        return {
            "model_id": model_id,
            "loaded": dep is not None and dep.status == "active",
            "artifact_valid": bool(version and version.artifact_path),
            "current_version": version.version if version else "",
            "prediction_latency_ms": 0.0,
            "recent_errors": 0,
            "deployment_state": dep.status if dep else "none",
            "health_status": dep.health_status if dep else "unknown",
        }

    def _audit(self, action: str, resource_id: str, org_id: str, details: dict) -> None:
        with contextlib.suppress(Exception):
            from app.admin.services.platform import PlatformAdmin

            platform = PlatformAdmin()
            platform.audit.append(
                action=action,
                resource_type="mlops_deployment",
                resource_id=resource_id,
                organization_id=org_id,
                details=details,
            )

    def _metrics(self, name: str, value: float, **labels: str) -> None:
        with contextlib.suppress(Exception):
            from app.admin.services.platform import PlatformAdmin

            platform = PlatformAdmin()
            platform.metrics.record(name, value, labels=labels or None)
