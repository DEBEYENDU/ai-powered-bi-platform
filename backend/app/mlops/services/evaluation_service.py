"""Model evaluation service."""

from __future__ import annotations

import contextlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.mlops.models.model import MLOpsEvaluation, MLOpsModelVersion

log = get_logger("mlops.evaluation")


class EvaluationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_evaluation(self, data: dict[str, Any], organization_id: str) -> MLOpsEvaluation:
        evaluation = MLOpsEvaluation(
            model_version_id=data["model_version_id"],
            organization_id=organization_id,
            dataset_id=data.get("dataset_id", ""),
            dataset_name=data.get("dataset_name", ""),
            metrics=data.get("metrics", {}),
            metric_definitions=data.get("metric_definitions", {}),
            evaluation_type=data.get("evaluation_type", "test"),
            sample_count=data.get("sample_count", 0),
        )
        self.db.add(evaluation)

        version = self.db.scalars(
            select(MLOpsModelVersion).where(MLOpsModelVersion.id == data["model_version_id"])
        ).first()
        if version:
            version.metrics = data.get("metrics", {})
            version.evaluation_id = None  # Will be set after commit

        self.db.commit()
        self.db.refresh(evaluation)

        if version:
            version.evaluation_id = evaluation.id
            version.status = "validated"
            self.db.commit()

        self._audit(
            "evaluation_completed",
            evaluation.id,
            organization_id,
            {"metrics": data.get("metrics", {})},
        )
        self._metrics("mlops_evaluations_total", 1.0)
        log.info("evaluation_created", evaluation_id=evaluation.id)
        return evaluation

    def get_evaluation(self, evaluation_id: str, organization_id: str) -> MLOpsEvaluation | None:
        stmt = select(MLOpsEvaluation).where(
            MLOpsEvaluation.id == evaluation_id,
            MLOpsEvaluation.organization_id == organization_id,
        )
        return self.db.scalars(stmt).first()

    def get_evaluation_for_version(self, version_id: str) -> MLOpsEvaluation | None:
        stmt = select(MLOpsEvaluation).where(MLOpsEvaluation.model_version_id == version_id)
        return self.db.scalars(stmt).first()

    def list_evaluations(
        self, organization_id: str, model_version_id: str | None = None
    ) -> list[MLOpsEvaluation]:
        stmt = select(MLOpsEvaluation).where(MLOpsEvaluation.organization_id == organization_id)
        if model_version_id:
            stmt = stmt.where(MLOpsEvaluation.model_version_id == model_version_id)
        return list(self.db.scalars(stmt.order_by(MLOpsEvaluation.created_at.desc()).all()))

    def compare_versions(self, version_ids: list[str], organization_id: str) -> dict[str, Any]:
        versions_data = []
        best_version = ""
        best_metric = float("inf")

        for vid in version_ids:
            version = self.db.scalars(
                select(MLOpsModelVersion).where(
                    MLOpsModelVersion.id == vid,
                    MLOpsModelVersion.organization_id == organization_id,
                )
            ).first()
            if not version:
                continue

            eval_rec = self.get_evaluation_for_version(vid)
            metrics = eval_rec.metrics if eval_rec else version.metrics

            versions_data.append(
                {
                    "version_id": vid,
                    "version": version.version,
                    "metrics": metrics,
                    "hyperparameters": version.hyperparameters,
                    "framework": version.framework,
                    "training_dataset_id": version.training_dataset_id,
                    "status": version.status,
                    "created_at": str(version.created_at),
                }
            )

            rmse = metrics.get("rmse", metrics.get("rmse", float("inf")))
            if isinstance(rmse, (int, float)) and rmse < best_metric:
                best_metric = rmse
                best_version = version.version

        return {
            "versions": versions_data,
            "best_version": best_version,
            "comparison_metric": "rmse",
        }

    def _audit(self, action: str, resource_id: str, org_id: str, details: dict) -> None:
        with contextlib.suppress(Exception):
            from app.admin.services.platform import PlatformAdmin

            platform = PlatformAdmin()
            platform.audit.append(
                action=action,
                resource_type="mlops_evaluation",
                resource_id=resource_id,
                organization_id=org_id,
                details=details,
            )

    def _metrics(self, name: str, value: float, **labels: str) -> None:
        with contextlib.suppress(Exception):
            from app.admin.services.platform import PlatformAdmin

            platform = PlatformAdmin()
            platform.metrics.record(name, value, labels=labels or None)
