"""Model registry service — CRUD for models and versions."""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.mlops.engine.lifecycle import (
    LifecycleError,
    can_promote_to_production,
    validate_model_transition,
    validate_version_transition,
)
from app.mlops.models.model import (
    MLOpsEvaluation,
    MLOpsModel,
    MLOpsModelVersion,
)

log = get_logger("mlops.registry")


class ModelRegistryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Models ---

    def create_model(self, data: dict[str, Any], organization_id: str, owner_id: str) -> MLOpsModel:
        model = MLOpsModel(
            organization_id=organization_id,
            name=data["name"],
            description=data.get("description", ""),
            model_type=data["model_type"],
            task_type=data["task_type"],
            framework=data.get("framework", "sklearn"),
            owner_id=owner_id,
            tags=data.get("tags", []),
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        self._audit("model_registered", model.id, organization_id, {"name": model.name})
        self._metrics("mlops_models_total", 1.0)
        log.info("model_created", model_id=model.id, name=model.name)
        return model

    def get_model(self, model_id: str, organization_id: str) -> MLOpsModel | None:
        stmt = select(MLOpsModel).where(
            MLOpsModel.id == model_id,
            MLOpsModel.organization_id == organization_id,
            MLOpsModel.deleted_at.is_(None),
        )
        return self.db.scalars(stmt).first()

    def list_models(self, organization_id: str, status: str | None = None) -> list[MLOpsModel]:
        stmt = select(MLOpsModel).where(
            MLOpsModel.organization_id == organization_id,
            MLOpsModel.deleted_at.is_(None),
        )
        if status:
            stmt = stmt.where(MLOpsModel.status == status)
        return list(self.db.scalars(stmt).all())

    def update_model(
        self, model_id: str, organization_id: str, data: dict[str, Any]
    ) -> MLOpsModel | None:
        model = self.get_model(model_id, organization_id)
        if not model:
            return None
        for key, value in data.items():
            if hasattr(model, key) and value is not None:
                if key == "status":
                    validate_model_transition(model.status, value)
                setattr(model, key, value)
        model.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(model)
        self._audit("model_updated", model_id, organization_id, data)
        return model

    def delete_model(self, model_id: str, organization_id: str) -> bool:
        model = self.get_model(model_id, organization_id)
        if not model:
            return False
        model.deleted_at = datetime.utcnow()
        self.db.commit()
        self._audit("model_deleted", model_id, organization_id, {})
        return True

    # --- Versions ---

    def create_version(
        self, model_id: str, organization_id: str, data: dict[str, Any], created_by: str = ""
    ) -> MLOpsModelVersion:
        model = self.get_model(model_id, organization_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        existing = self.db.scalars(
            select(MLOpsModelVersion).where(
                MLOpsModelVersion.model_id == model_id,
                MLOpsModelVersion.organization_id == organization_id,
            )
        ).all()
        next_number = len(existing) + 1

        version = MLOpsModelVersion(
            model_id=model_id,
            organization_id=organization_id,
            version=f"v{next_number}",
            version_number=next_number,
            artifact_path=data.get("artifact_path", ""),
            checksum=data.get("checksum", ""),
            framework=data.get("framework", model.framework),
            runtime_version=data.get("runtime_version", ""),
            training_dataset_id=data.get("training_dataset_id", ""),
            training_run_id=data.get("training_run_id"),
            feature_schema=data.get("feature_schema", {}),
            hyperparameters=data.get("hyperparameters", {}),
            metrics=data.get("metrics", {}),
            created_by=created_by,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)

        if model.status == "draft":
            model.status = "registered"
            model.updated_at = datetime.utcnow()
            self.db.commit()

        self._audit(
            "version_created",
            version.id,
            organization_id,
            {"model_id": model_id, "version": version.version},
        )
        self._metrics("mlops_versions_total", 1.0)
        log.info("version_created", model_id=model_id, version=version.version)
        return version

    def get_version(self, version_id: str, organization_id: str) -> MLOpsModelVersion | None:
        stmt = select(MLOpsModelVersion).where(
            MLOpsModelVersion.id == version_id,
            MLOpsModelVersion.organization_id == organization_id,
        )
        return self.db.scalars(stmt).first()

    def get_version_by_model_and_version(
        self, model_id: str, version: str, organization_id: str
    ) -> MLOpsModelVersion | None:
        stmt = select(MLOpsModelVersion).where(
            MLOpsModelVersion.model_id == model_id,
            MLOpsModelVersion.version == version,
            MLOpsModelVersion.organization_id == organization_id,
        )
        return self.db.scalars(stmt).first()

    def list_versions(self, model_id: str, organization_id: str) -> list[MLOpsModelVersion]:
        stmt = (
            select(MLOpsModelVersion)
            .where(
                MLOpsModelVersion.model_id == model_id,
                MLOpsModelVersion.organization_id == organization_id,
            )
            .order_by(MLOpsModelVersion.version_number)
        )
        return list(self.db.scalars(stmt).all())

    def promote_version(
        self, version_id: str, organization_id: str, target_environment: str = "production"
    ) -> MLOpsModelVersion:
        version = self.get_version(version_id, organization_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        has_eval = (
            self.db.scalars(
                select(MLOpsEvaluation).where(MLOpsEvaluation.model_version_id == version_id)
            ).first()
            is not None
        )

        allowed, _blockers = can_promote_to_production(
            version.status, has_eval, bool(version.artifact_path)
        )
        if not allowed:
            raise LifecycleError(version.status, "production", "version")

        model = self.get_model(version.model_id, organization_id)
        if model and model.status == "staging":
            model.status = "production"
            model.updated_at = datetime.utcnow()

        for v in self.list_versions(version.model_id, organization_id):
            if v.id != version_id and v.is_active:
                v.is_active = False
        version.is_active = True
        version.status = "production"

        self.db.commit()
        self._audit(
            "version_promoted",
            version_id,
            organization_id,
            {"version": version.version, "environment": target_environment},
        )
        self._metrics("mlops_promotions_total", 1.0)
        log.info("version_promoted", version_id=version_id, version=version.version)
        return version

    def archive_version(self, version_id: str, organization_id: str) -> MLOpsModelVersion:
        version = self.get_version(version_id, organization_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")
        validate_version_transition(version.status, "archived")
        version.status = "archived"
        version.is_active = False
        self.db.commit()
        self._audit("version_archived", version_id, organization_id, {})
        return version

    def compare_versions(
        self, version_ids: list[str], organization_id: str
    ) -> list[dict[str, Any]]:
        results = []
        for vid in version_ids:
            v = self.get_version(vid, organization_id)
            if v:
                results.append(
                    {
                        "id": v.id,
                        "version": v.version,
                        "metrics": v.metrics,
                        "hyperparameters": v.hyperparameters,
                        "framework": v.framework,
                        "training_dataset_id": v.training_dataset_id,
                        "status": v.status,
                        "created_at": str(v.created_at),
                    }
                )
        return results

    def _audit(self, action: str, resource_id: str, org_id: str, details: dict) -> None:
        with contextlib.suppress(Exception):
            from app.admin.services.platform import PlatformAdmin

            platform = PlatformAdmin()
            platform.audit.append(
                action=action,
                resource_type="mlops_model",
                resource_id=resource_id,
                organization_id=org_id,
                details=details,
            )

    def _metrics(self, name: str, value: float, **labels: str) -> None:
        with contextlib.suppress(Exception):
            from app.admin.services.platform import PlatformAdmin

            platform = PlatformAdmin()
            platform.metrics.record(name, value, labels=labels or None)
