"""Training lifecycle service — orchestrates training runs."""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.mlops.models.model import MLOpsTrainingRun

log = get_logger("mlops.training")


class TrainingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def start_training(
        self, data: dict[str, Any], organization_id: str, created_by: str = ""
    ) -> MLOpsTrainingRun:
        run = MLOpsTrainingRun(
            experiment_id=data.get("experiment_id", ""),
            model_id=data.get("model_id"),
            organization_id=organization_id,
            dataset_id=data.get("dataset_id", ""),
            target_column=data.get("target_column", ""),
            status="running",
            parameters=data.get("parameters", {}),
            created_by=created_by,
            started_at=datetime.utcnow(),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        self._audit("training_started", run.id, organization_id, {"dataset_id": run.dataset_id})
        self._metrics("mlops_training_count", 1.0)
        log.info("training_started", run_id=run.id)
        return run

    def complete_training(
        self, run_id: str, organization_id: str, metrics: dict[str, Any], artifact_path: str = ""
    ) -> MLOpsTrainingRun | None:
        run = self._get_run(run_id, organization_id)
        if not run:
            return None
        run.status = "completed"
        run.metrics = metrics
        run.artifact_path = artifact_path
        run.completed_at = datetime.utcnow()
        if run.started_at:
            run.duration_ms = int((run.completed_at - run.started_at).total_seconds() * 1000)
        self.db.commit()
        self.db.refresh(run)
        self._audit("training_completed", run_id, organization_id, {"metrics": metrics})
        log.info("training_completed", run_id=run_id, duration_ms=run.duration_ms)
        return run

    def fail_training(
        self, run_id: str, organization_id: str, error_message: str
    ) -> MLOpsTrainingRun | None:
        run = self._get_run(run_id, organization_id)
        if not run:
            return None
        run.status = "failed"
        run.error_message = error_message
        run.completed_at = datetime.utcnow()
        if run.started_at:
            run.duration_ms = int((run.completed_at - run.started_at).total_seconds() * 1000)
        self.db.commit()
        self._audit("training_failed", run_id, organization_id, {"error": error_message})
        self._metrics("mlops_training_failures", 1.0)
        log.error("training_failed", run_id=run_id, error=error_message)
        return run

    def cancel_training(self, run_id: str, organization_id: str) -> MLOpsTrainingRun | None:
        run = self._get_run(run_id, organization_id)
        if not run or run.status not in ("queued", "running"):
            return None
        run.status = "cancelled"
        run.completed_at = datetime.utcnow()
        self.db.commit()
        self._audit("training_cancelled", run_id, organization_id, {})
        return run

    def get_run(self, run_id: str, organization_id: str) -> MLOpsTrainingRun | None:
        return self._get_run(run_id, organization_id)

    def list_runs(
        self, organization_id: str, model_id: str | None = None
    ) -> list[MLOpsTrainingRun]:
        stmt = select(MLOpsTrainingRun).where(MLOpsTrainingRun.organization_id == organization_id)
        if model_id:
            stmt = stmt.where(MLOpsTrainingRun.model_id == model_id)
        return list(self.db.scalars(stmt.order_by(MLOpsTrainingRun.created_at.desc()).all()))

    def _get_run(self, run_id: str, organization_id: str) -> MLOpsTrainingRun | None:
        stmt = select(MLOpsTrainingRun).where(
            MLOpsTrainingRun.id == run_id,
            MLOpsTrainingRun.organization_id == organization_id,
        )
        return self.db.scalars(stmt).first()

    def _audit(self, action: str, resource_id: str, org_id: str, details: dict) -> None:
        with contextlib.suppress(Exception):
            from app.admin.services.platform import PlatformAdmin

            platform = PlatformAdmin()
            platform.audit.append(
                action=action,
                resource_type="mlops_training",
                resource_id=resource_id,
                organization_id=org_id,
                details=details,
            )

    def _metrics(self, name: str, value: float, **labels: str) -> None:
        with contextlib.suppress(Exception):
            from app.admin.services.platform import PlatformAdmin

            platform = PlatformAdmin()
            platform.metrics.record(name, value, labels=labels or None)
