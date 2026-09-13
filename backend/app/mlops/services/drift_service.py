"""Drift detection service — data drift, prediction drift, performance degradation."""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.mlops.models.model import MLOpsMonitoringRecord

log = get_logger("mlops.drift")


class DriftService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def check_data_drift(
        self,
        model_id: str,
        organization_id: str,
        reference_stats: dict[str, Any],
        current_stats: dict[str, Any],
    ) -> dict[str, Any]:
        drifts: list[dict[str, Any]] = []

        for feature, ref_val in reference_stats.items():
            cur_val = current_stats.get(feature)
            if cur_val is None:
                continue

            if isinstance(ref_val, dict) and isinstance(cur_val, dict):
                ref_mean = ref_val.get("mean", 0)
                cur_mean = cur_val.get("mean", 0)
                ref_std = ref_val.get("std", 1) or 1
                cur_std = cur_val.get("std", 1) or 1

                mean_shift = abs(cur_mean - ref_mean) / max(abs(ref_mean), 1e-10)
                var_ratio = (cur_std**2) / max(ref_std**2, 1e-10)

                if mean_shift > 0.1 or abs(var_ratio - 1) > 0.5:
                    severity = (
                        "high" if mean_shift > 0.3 else "medium" if mean_shift > 0.1 else "low"
                    )
                    drifts.append(
                        {
                            "drift_type": "data_drift",
                            "severity": severity,
                            "feature": feature,
                            "description": f"{feature}: mean shift={mean_shift:.2%}, variance ratio={var_ratio:.2f}",
                            "metrics": {
                                "mean_shift": round(mean_shift, 4),
                                "variance_ratio": round(var_ratio, 4),
                            },
                            "recommended_action": f"Investigate distribution changes in '{feature}'",
                        }
                    )

        status = (
            "critical"
            if any(d["severity"] == "high" for d in drifts)
            else "warning"
            if drifts
            else "normal"
        )

        self._record_drift_events(model_id, organization_id, drifts)

        return {
            "status": status,
            "drifts": drifts,
            "overall_health": status,
            "retraining_recommended": len([d for d in drifts if d["severity"] == "high"]) > 0,
        }

    def check_prediction_drift(
        self,
        model_id: str,
        organization_id: str,
        historical_predictions: list[float],
        recent_predictions: list[float],
    ) -> dict[str, Any]:
        drifts: list[dict[str, Any]] = []

        if len(historical_predictions) < 10 or len(recent_predictions) < 5:
            return {
                "status": "insufficient_data",
                "drifts": [],
                "overall_health": "insufficient_data",
                "retraining_recommended": False,
            }

        import numpy as np
        from scipy import stats as sp_stats

        ref = np.array(historical_predictions)
        cur = np.array(recent_predictions)

        _ks_stat, ks_p = sp_stats.ks_2samp(ref, cur)
        mean_drift = abs(cur.mean() - ref.mean()) / max(abs(ref.mean()), 1e-10)

        if ks_p < 0.05 or mean_drift > 0.1:
            severity = "high" if mean_drift > 0.3 else "medium" if mean_drift > 0.1 else "low"
            drifts.append(
                {
                    "drift_type": "prediction_drift",
                    "severity": severity,
                    "feature": "predictions",
                    "description": f"Prediction drift: mean shift={mean_drift:.2%}, KS p={ks_p:.4f}",
                    "metrics": {
                        "mean_drift": round(float(mean_drift), 4),
                        "ks_p_value": round(float(ks_p), 4),
                    },
                    "recommended_action": "Retrain model with recent data",
                }
            )

        status = (
            "critical"
            if any(d["severity"] == "high" for d in drifts)
            else "warning"
            if drifts
            else "normal"
        )
        self._record_drift_events(model_id, organization_id, drifts)

        return {
            "status": status,
            "drifts": drifts,
            "overall_health": status,
            "retraining_recommended": len([d for d in drifts if d["severity"] == "high"]) > 0,
        }

    def get_drift_history(
        self, model_id: str, organization_id: str, days: int = 30
    ) -> list[MLOpsMonitoringRecord]:
        since = datetime.utcnow() - timedelta(days=days)
        stmt = select(MLOpsMonitoringRecord).where(
            MLOpsMonitoringRecord.model_id == model_id,
            MLOpsMonitoringRecord.organization_id == organization_id,
            MLOpsMonitoringRecord.metric_type.in_(["data_drift", "prediction_drift"]),
            MLOpsMonitoringRecord.recorded_at >= since,
        )
        return list(self.db.scalars(stmt.order_by(MLOpsMonitoringRecord.recorded_at.desc()).all()))

    def _record_drift_events(self, model_id: str, organization_id: str, drifts: list[dict]) -> None:
        for drift in drifts:
            with contextlib.suppress(Exception):
                record = MLOpsMonitoringRecord(
                    model_id=model_id,
                    organization_id=organization_id,
                    metric_type=drift["drift_type"],
                    metric_name=f"drift_{drift['feature']}",
                    metric_value=drift["metrics"].get(
                        "mean_shift", drift["metrics"].get("mean_drift", 0)
                    ),
                    dimensions=drift["metrics"],
                    status=drift["severity"],
                    message=drift["description"],
                )
                self.db.add(record)
            self.db.commit()

    def _audit(self, action: str, resource_id: str, org_id: str, details: dict) -> None:
        with contextlib.suppress(Exception):
            from app.admin.services.platform import PlatformAdmin

            platform = PlatformAdmin()
            platform.audit.append(
                action=action,
                resource_type="mlops_drift",
                resource_id=resource_id,
                organization_id=org_id,
                details=details,
            )
