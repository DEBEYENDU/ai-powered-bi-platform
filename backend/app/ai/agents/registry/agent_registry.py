"""Agent registry — central registry for all agent types.
New agents register themselves here without modifying existing code."""

from __future__ import annotations

import time
from typing import Any, Protocol


class Agent(Protocol):
    """Protocol that all agents must implement."""

    agent_type: str
    name: str

    async def execute(
        self, task: str, context: dict[str, Any], tools: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...


class AgentRegistry:
    """Central registry for agent types."""

    def __init__(self) -> None:
        self._agents: dict[str, type] = {}
        self._instances: dict[str, Any] = {}
        self._status: dict[str, dict[str, Any]] = {}
        self._metrics: dict[str, dict[str, Any]] = {}

    def register(self, agent_class: type, agent_type: str | None = None) -> None:
        """Register an agent class. The agent_type is read from the class if not provided."""
        atype = agent_type or getattr(agent_class, "agent_type", agent_class.__name__.lower())
        self._agents[atype] = agent_class
        self._status[atype] = {
            "status": "ready",
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_duration_ms": 0.0,
            "last_active": "",
        }
        self._metrics[atype] = {
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_duration_ms": 0.0,
        }

    def get(self, agent_type: str) -> Any:
        """Get or create an agent instance."""
        if agent_type not in self._agents:
            raise KeyError(f"Agent '{agent_type}' not registered")
        if agent_type not in self._instances:
            self._instances[agent_type] = self._agents[agent_type]()
        return self._instances[agent_type]

    def has(self, agent_type: str) -> bool:
        return agent_type in self._agents

    def list_types(self) -> list[str]:
        return list(self._agents.keys())

    def list_all(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for atype, cls in self._agents.items():
            status = self._status.get(atype, {})
            metrics = self._metrics.get(atype, {})
            result.append(
                {
                    "agent_type": atype,
                    "name": getattr(cls, "name", atype),
                    "status": status.get("status", "unknown"),
                    "tasks_completed": status.get("tasks_completed", 0),
                    "tasks_failed": status.get("tasks_failed", 0),
                    "avg_duration_ms": metrics.get("avg_duration_ms", 0),
                    "last_active": status.get("last_active", ""),
                }
            )
        return result

    def record_success(self, agent_type: str, duration_ms: float) -> None:
        if agent_type in self._status:
            s = self._status[agent_type]
            s["tasks_completed"] += 1
            s["last_active"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            total = s["total_duration_ms"] + duration_ms
            s["total_duration_ms"] = total
            count = s["tasks_completed"]
            self._metrics[agent_type]["avg_duration_ms"] = total / max(count, 1)

    def record_failure(self, agent_type: str) -> None:
        if agent_type in self._status:
            self._status[agent_type]["tasks_failed"] += 1
            self._status[agent_type]["last_active"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    def set_busy(self, agent_type: str) -> None:
        if agent_type in self._status:
            self._status[agent_type]["status"] = "busy"

    def set_ready(self, agent_type: str) -> None:
        if agent_type in self._status:
            self._status[agent_type]["status"] = "ready"


# Singleton
_registry: AgentRegistry | None = None


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
