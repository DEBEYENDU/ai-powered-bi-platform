"""Workflow monitoring and metrics."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from app.core.logging import get_logger

log = get_logger("workflow.monitoring")


class WorkflowMonitor:
    """Tracks workflow execution metrics and statistics."""

    def __init__(self) -> None:
        self._metrics: dict[str, Any] = defaultdict(
            lambda: {
                "total": 0,
                "success": 0,
                "failure": 0,
                "total_duration_ms": 0.0,
            }
        )
        self._step_metrics: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "calls": 0,
                "success": 0,
                "failure": 0,
                "total_duration_ms": 0.0,
            }
        )
        self._recent_executions: list[dict[str, Any]] = []

    def record_execution(
        self,
        workflow_id: str,
        status: str,
        duration_ms: float,
        execution_id: str = "",
    ) -> None:
        m = self._metrics[workflow_id]
        m["total"] += 1
        if status == "completed":
            m["success"] += 1
        else:
            m["failure"] += 1
        m["total_duration_ms"] += duration_ms

        self._recent_executions.append(
            {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "status": status,
                "duration_ms": round(duration_ms, 1),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        if len(self._recent_executions) > 500:
            self._recent_executions = self._recent_executions[-500:]

    def record_step(
        self,
        step_id: str,
        action_type: str,
        status: str,
        duration_ms: float,
    ) -> None:
        key = f"{action_type}:{step_id}"
        m = self._step_metrics[key]
        m["calls"] += 1
        if status == "completed":
            m["success"] += 1
        else:
            m["failure"] += 1
        m["total_duration_ms"] += duration_ms

    def get_workflow_stats(self, workflow_id: str) -> dict[str, Any]:
        m = self._metrics.get(workflow_id, {})
        total = m.get("total", 0)
        return {
            "total_executions": total,
            "successful": m.get("success", 0),
            "failed": m.get("failure", 0),
            "success_rate": round(m["success"] / max(total, 1) * 100, 1),
            "avg_duration_ms": round(m.get("total_duration_ms", 0) / max(total, 1), 1),
        }

    def get_global_stats(self) -> dict[str, Any]:
        total_exec = sum(m["total"] for m in self._metrics.values())
        total_success = sum(m["success"] for m in self._metrics.values())
        total_failure = sum(m["failure"] for m in self._metrics.values())
        total_duration = sum(m["total_duration_ms"] for m in self._metrics.values())

        return {
            "total_workflows_tracked": len(self._metrics),
            "total_executions": total_exec,
            "total_success": total_success,
            "total_failure": total_failure,
            "success_rate": round(total_success / max(total_exec, 1) * 100, 1),
            "avg_duration_ms": round(total_duration / max(total_exec, 1), 1),
            "recent_executions": len(self._recent_executions),
        }

    def get_step_stats(self) -> dict[str, Any]:
        return dict(self._step_metrics)

    def get_recent_executions(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._recent_executions[-limit:]


# Singleton
_monitor: WorkflowMonitor | None = None


def get_monitor() -> WorkflowMonitor:
    global _monitor
    if _monitor is None:
        _monitor = WorkflowMonitor()
    return _monitor
