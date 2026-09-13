"""Model serving service — prediction interface."""

from __future__ import annotations

import contextlib
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.mlops.models.model import (
    MLOpsDeployment,
    MLOpsModel,
    MLOpsModelVersion,
    MLOpsMonitoringRecord,
)

log = get_logger("mlops.serving")


class ServingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def predict(
        self,
        model_id: str,
        organization_id: str,
        input_data: dict[str, Any],
        version: str | None = None,
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

        if version:
            model_version = self.db.scalars(
                select(MLOpsModelVersion).where(
                    MLOpsModelVersion.model_id == model_id,
                    MLOpsModelVersion.version == version,
                    MLOpsModelVersion.organization_id == organization_id,
                )
            ).first()
        else:
            model_version = self.db.scalars(
                select(MLOpsModelVersion).where(
                    MLOpsModelVersion.model_id == model_id,
                    MLOpsModelVersion.is_active.is_(True),
                    MLOpsModelVersion.organization_id == organization_id,
                )
            ).first()

        if not model_version:
            raise ValueError(f"No active version found for model {model_id}")

        dep = self.db.scalars(
            select(MLOpsDeployment).where(
                MLOpsDeployment.model_id == model_id,
                MLOpsDeployment.model_version_id == model_version.id,
                MLOpsDeployment.environment == "production",
                MLOpsDeployment.status == "active",
                MLOpsDeployment.organization_id == organization_id,
            )
        ).first()

        if not dep:
            raise ValueError(f"No active production deployment for model {model_id}")

        start = time.time()
        try:
            prediction = self._run_prediction(model_version, input_data)
            latency_ms = (time.time() - start) * 1000

            self._record_metric(
                model_id, model_version.id, organization_id, "prediction_count", 1.0
            )
            self._record_metric(model_id, model_version.id, organization_id, "latency", latency_ms)

            return {
                "success": True,
                "model_id": model_id,
                "version": model_version.version,
                "prediction": prediction,
                "latency_ms": round(latency_ms, 2),
            }
        except Exception as exc:
            latency_ms = (time.time() - start) * 1000
            self._record_metric(model_id, model_version.id, organization_id, "error_rate", 1.0)
            log.error("prediction_failed", model_id=model_id, error=str(exc))
            return {
                "success": False,
                "model_id": model_id,
                "version": model_version.version,
                "error": str(exc),
                "latency_ms": round(latency_ms, 2),
            }

    def _run_prediction(self, version: MLOpsModelVersion, input_data: dict[str, Any]) -> Any:
        feature_schema = version.feature_schema or {}
        features = feature_schema.get("features", [])

        if features:
            for feat in features:
                name = feat.get("name", "")
                if name and name not in input_data:
                    raise ValueError(f"Missing required feature: {name}")

        return {
            "result": "prediction_placeholder",
            "model_version": version.version,
            "features_used": list(input_data.keys()),
        }

    def _record_metric(
        self, model_id: str, version_id: str, org_id: str, name: str, value: float
    ) -> None:
        with contextlib.suppress(Exception):
            record = MLOpsMonitoringRecord(
                model_id=model_id,
                model_version_id=version_id,
                organization_id=org_id,
                metric_type="serving",
                metric_name=name,
                metric_value=value,
            )
            self.db.add(record)
            self.db.commit()
