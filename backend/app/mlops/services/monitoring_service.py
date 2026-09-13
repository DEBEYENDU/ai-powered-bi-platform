"""Model monitoring service."""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.mlops.models.model import MLOpsMonitoringRecord

log = get_logger("mlops.monitoring")


class MonitoringService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record_metric(
        self,
        model_id: str,
        organization_id: str,
        metric_type: str,
        metric_name: str,
        value: float,
        dimensions: dict | None = None,
        model_version_id: str | None = None,
    ) -> MLOpsMonitoringRecord:
        record = MLOpsMonitoringRecord(
            model_id=model_id,
            model_version_id=model_version_id,
            organization_id=organization_id,
            metric_type=metric_type,
            metric_name=metric_name,
            metric_value=value,
            dimensions=dimensions or {},
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_summary(self, model_id: str, organization_id: str, hours: int = 24) -> dict[str, Any]:
        since = datetime.utcnow() - timedelta(hours=hours)
        stmt = select(MLOpsMonitoringRecord).where(
            MLOpsMonitoringRecord.model_id == model_id,
            MLOpsMonitoringRecord.organization_id == organization_id,
            MLOpsMonitoringRecord.recorded_at >= since,
        )
        records = list(self.db.scalars(stmt).all())

        total_predictions = sum(1 for r in records if r.metric_name == "prediction_count")
        latencies = [r.metric_value for r in records if r.metric_name == "latency"]
        errors = sum(1 for r in records if r.metric_name == "error_rate")
        drift_scores = [
            r.metric_value for r in records if r.metric_name in ("data_drift", "prediction_drift")
        ]
        perf_scores = [r.metric_value for r in records if r.metric_name == "performance"]

        return {
            "model_id": model_id,
            "period_hours": hours,
            "total_predictions": total_predictions,
            "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1), 2),
            "error_rate": round(errors / max(total_predictions, 1), 4),
            "data_drift_score": round(sum(drift_scores) / max(len(drift_scores), 1), 4),
            "prediction_drift_score": 0.0,
            "performance_score": round(sum(perf_scores) / max(len(perf_scores), 1), 4)
            if perf_scores
            else 0.0,
        }

    def get_metrics(
        self, model_id: str, organization_id: str, metric_type: str | None = None, limit: int = 100
    ) -> list[MLOpsMonitoringRecord]:
        stmt = select(MLOpsMonitoringRecord).where(
            MLOpsMonitoringRecord.model_id == model_id,
            MLOpsMonitoringRecord.organization_id == organization_id,
        )
        if metric_type:
            stmt = stmt.where(MLOpsMonitoringRecord.metric_type == metric_type)
        return list(
            self.db.scalars(
                stmt.order_by(MLOpsMonitoringRecord.recorded_at.desc()).limit(limit).all()
            )
        )

    def check_alerts(self, model_id: str, organization_id: str) -> list[dict[str, Any]]:
        summary = self.get_summary(model_id, organization_id, hours=1)
        alerts = []

        if summary["error_rate"] > 0.05:
            alerts.append(
                {
                    "type": "high_error_rate",
                    "severity": "high",
                    "value": summary["error_rate"],
                    "message": f"Error rate {summary['error_rate']:.1%} exceeds 5% threshold",
                }
            )

        if summary["avg_latency_ms"] > 1000:
            alerts.append(
                {
                    "type": "high_latency",
                    "severity": "medium",
                    "value": summary["avg_latency_ms"],
                    "message": f"Average latency {summary['avg_latency_ms']:.0f}ms exceeds 1000ms threshold",
                }
            )

        return alerts

    def _audit(self, action: str, resource_id: str, org_id: str, details: dict) -> None:
        with contextlib.suppress(Exception):
            from app.admin.services.platform import PlatformAdmin

            platform = PlatformAdmin()
            platform.audit.append(
                action=action,
                resource_type="mlops_monitoring",
                resource_id=resource_id,
                organization_id=org_id,
                details=details,
            )
