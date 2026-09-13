"""Lifecycle service — orchestrates the full model lifecycle."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.mlops.engine.lifecycle import get_lifecycle_summary
from app.mlops.services.deployment_service import DeploymentService
from app.mlops.services.evaluation_service import EvaluationService
from app.mlops.services.model_registry import ModelRegistryService
from app.mlops.services.monitoring_service import MonitoringService

log = get_logger("mlops.lifecycle")


class LifecycleService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.registry = ModelRegistryService(db)
        self.evaluation = EvaluationService(db)
        self.deployment = DeploymentService(db)
        self.monitoring = MonitoringService(db)

    def get_model_lifecycle(self, model_id: str, organization_id: str) -> dict[str, Any]:
        model = self.registry.get_model(model_id, organization_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        versions = self.registry.list_versions(model_id, organization_id)
        active_version = next((v for v in versions if v.is_active), None)
        deployment = self.deployment.get_active_deployment(model_id, organization_id)
        monitoring = self.monitoring.get_summary(model_id, organization_id)

        summary = get_lifecycle_summary(
            model.status,
            active_version.status if active_version else None,
            deployment.status if deployment else None,
        )

        return {
            "model": {
                "id": model.id,
                "name": model.name,
                "model_type": model.model_type,
                "task_type": model.task_type,
                "status": model.status,
                "framework": model.framework,
                "created_at": str(model.created_at),
            },
            "versions": [
                {
                    "id": v.id,
                    "version": v.version,
                    "status": v.status,
                    "metrics": v.metrics,
                    "created_at": str(v.created_at),
                }
                for v in versions
            ],
            "active_version": {
                "id": active_version.id,
                "version": active_version.version,
                "status": active_version.status,
            }
            if active_version
            else None,
            "deployment": {
                "id": deployment.id,
                "environment": deployment.environment,
                "status": deployment.status,
                "health_status": deployment.health_status,
            }
            if deployment
            else None,
            "monitoring": monitoring,
            "lifecycle": summary,
        }

    def get_overview(self, organization_id: str) -> dict[str, Any]:
        models = self.registry.list_models(organization_id)

        status_counts: dict[str, int] = {}
        for m in models:
            status_counts[m.status] = status_counts.get(m.status, 0) + 1

        total_versions = sum(
            len(self.registry.list_versions(m.id, organization_id)) for m in models
        )
        total_deployments = len(self.deployment.list_deployments(organization_id))

        return {
            "total_models": len(models),
            "total_versions": total_versions,
            "total_deployments": total_deployments,
            "status_distribution": status_counts,
            "models": [
                {
                    "id": m.id,
                    "name": m.name,
                    "model_type": m.model_type,
                    "status": m.status,
                    "framework": m.framework,
                    "created_at": str(m.created_at),
                }
                for m in models
            ],
        }
