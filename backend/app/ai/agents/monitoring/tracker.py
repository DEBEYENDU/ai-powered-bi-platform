"""Metrics, logs, and execution history tracker."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import Any

from app.ai.agents.schemas import AgentLog, ExecutionMetrics


class ExecutionTracker:
    """Tracks execution metrics, logs, and task history across agents."""

    def __init__(self) -> None:
        self._logs: list[AgentLog] = []
        self._task_history: list[dict[str, Any]] = []
        self._metrics_by_task: dict[str, ExecutionMetrics] = {}
        self._agent_metrics: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"calls": 0, "successes": 0, "failures": 0, "total_ms": 0.0}
        )

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log(
        self,
        level: str,
        agent_type: str,
        task_id: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> AgentLog:
        entry = AgentLog(
            id=str(uuid.uuid4())[:12],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            level=level,
            agent_type=agent_type,
            task_id=task_id,
            message=message,
            data=data or {},
        )
        self._logs.append(entry)
        return entry

    def get_logs(
        self,
        task_id: str | None = None,
        agent_type: str | None = None,
        level: str | None = None,
        limit: int = 100,
    ) -> list[AgentLog]:
        logs = self._logs
        if task_id:
            logs = [log for log in logs if log.task_id == task_id]
        if agent_type:
            logs = [log for log in logs if log.agent_type == agent_type]
        if level:
            logs = [log for log in logs if log.level == level]
        return logs[-limit:]

    # ------------------------------------------------------------------
    # Task history
    # ------------------------------------------------------------------

    def record_task(
        self,
        task_id: str,
        task: str,
        agent_sequence: list[str],
        metrics: ExecutionMetrics,
        answer: str = "",
    ) -> None:
        entry = {
            "task_id": task_id,
            "task": task,
            "agent_sequence": agent_sequence,
            "answer": answer,
            "duration_ms": metrics.total_duration_ms,
            "agents_called": metrics.agents_called,
            "failures": metrics.failures,
            "retries": metrics.retries,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self._task_history.append(entry)
        self._metrics_by_task[task_id] = metrics

        # Update per-agent metrics
        for step in metrics.steps:
            am = self._agent_metrics[step.agent_type]
            am["calls"] += 1
            if step.status == "completed":
                am["successes"] += 1
            else:
                am["failures"] += 1
            am["total_ms"] += step.duration_ms

    def get_task_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._task_history[-limit:]

    def get_task_metrics(self, task_id: str) -> ExecutionMetrics | None:
        return self._metrics_by_task.get(task_id)

    # ------------------------------------------------------------------
    # Agent-level metrics
    # ------------------------------------------------------------------

    def get_agent_metrics(self, agent_type: str | None = None) -> dict[str, Any]:
        if agent_type:
            am = self._agent_metrics.get(agent_type, {})
            avg = am["total_ms"] / max(am["calls"], 1)
            return {
                "agent_type": agent_type,
                "calls": am["calls"],
                "successes": am["successes"],
                "failures": am["failures"],
                "success_rate": round(am["successes"] / max(am["calls"], 1) * 100, 1),
                "avg_duration_ms": round(avg, 1),
            }
        return {
            at: {
                "calls": m["calls"],
                "successes": m["successes"],
                "failures": m["failures"],
                "success_rate": round(m["successes"] / max(m["calls"], 1) * 100, 1),
                "avg_duration_ms": round(m["total_ms"] / max(m["calls"], 1), 1),
            }
            for at, m in self._agent_metrics.items()
        }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_logs": len(self._logs),
            "total_tasks": len(self._task_history),
            "agents_used": len(self._agent_metrics),
        }


# Singleton
_tracker: ExecutionTracker | None = None


def get_tracker() -> ExecutionTracker:
    global _tracker
    if _tracker is None:
        _tracker = ExecutionTracker()
    return _tracker
