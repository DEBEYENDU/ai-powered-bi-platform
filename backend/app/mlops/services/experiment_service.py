"""Experiment tracking service."""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.mlops.models.model import MLOpsExperiment, MLOpsTrainingRun

log = get_logger("mlops.experiment")


class ExperimentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_experiment(
        self, data: dict[str, Any], organization_id: str, created_by: str = ""
    ) -> MLOpsExperiment:
        exp = MLOpsExperiment(
            organization_id=organization_id,
            name=data["name"],
            description=data.get("description", ""),
            objective=data.get("objective", ""),
            dataset_id=data.get("dataset_id", ""),
            model_id=data.get("model_id"),
            created_by=created_by,
        )
        self.db.add(exp)
        self.db.commit()
        self.db.refresh(exp)
        self._audit("experiment_created", exp.id, organization_id, {"name": exp.name})
        log.info("experiment_created", experiment_id=exp.id)
        return exp

    def get_experiment(self, experiment_id: str, organization_id: str) -> MLOpsExperiment | None:
        stmt = select(MLOpsExperiment).where(
            MLOpsExperiment.id == experiment_id,
            MLOpsExperiment.organization_id == organization_id,
        )
        return self.db.scalars(stmt).first()

    def list_experiments(self, organization_id: str) -> list[MLOpsExperiment]:
        stmt = (
            select(MLOpsExperiment)
            .where(
                MLOpsExperiment.organization_id == organization_id,
            )
            .order_by(MLOpsExperiment.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def update_experiment(
        self, experiment_id: str, organization_id: str, data: dict[str, Any]
    ) -> MLOpsExperiment | None:
        exp = self.get_experiment(experiment_id, organization_id)
        if not exp:
            return None
        for key, value in data.items():
            if hasattr(exp, key) and value is not None:
                setattr(exp, key, value)
        exp.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(exp)
        return exp

    def list_runs(self, experiment_id: str, organization_id: str) -> list[MLOpsTrainingRun]:
        stmt = (
            select(MLOpsTrainingRun)
            .where(
                MLOpsTrainingRun.experiment_id == experiment_id,
                MLOpsTrainingRun.organization_id == organization_id,
            )
            .order_by(MLOpsTrainingRun.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_run(self, run_id: str, organization_id: str) -> MLOpsTrainingRun | None:
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
                resource_type="mlops_experiment",
                resource_id=resource_id,
                organization_id=org_id,
                details=details,
            )
