"""Main orchestrator — entry point for the multi-agent platform."""

from __future__ import annotations

import time
from typing import Any

from app.ai.agents.communication.bus import get_bus
from app.ai.agents.coordinator.planner import decompose_task
from app.ai.agents.execution.runner import run_plan
from app.ai.agents.memory.store import get_memory_store
from app.ai.agents.monitoring.tracker import get_tracker
from app.ai.agents.registry.agent_registry import get_registry
from app.ai.agents.schemas import (
    AgentListResponse,
    AgentRunRequest,
    AgentRunResponse,
    AgentStatus,
    LogsResponse,
    MemoryEntry,
    MemoryResponse,
    TaskHistoryResponse,
)

# Register all agent types on import
_registry = get_registry()


def _ensure_agents_registered() -> None:
    """Lazily register all agent classes."""
    if _registry.list_types():
        return
    from app.ai.agents.agents.business_analyst import BusinessAnalystAgent
    from app.ai.agents.agents.dashboard_agent import DashboardAgent
    from app.ai.agents.agents.data_quality_agent import DataQualityAgent
    from app.ai.agents.agents.forecast_agent import ForecastAgent
    from app.ai.agents.agents.knowledge_agent import KnowledgeAgent
    from app.ai.agents.agents.report_agent import ReportAgent
    from app.ai.agents.agents.security_agent import SecurityAgent
    from app.ai.agents.agents.sql_agent import SQLAgent
    from app.ai.agents.agents.visualization_agent import VisualizationAgent
    from app.ai.agents.agents.workflow_agent import WorkflowAgent

    for cls in [
        SQLAgent,
        DashboardAgent,
        BusinessAnalystAgent,
        ForecastAgent,
        ReportAgent,
        DataQualityAgent,
        SecurityAgent,
        WorkflowAgent,
        KnowledgeAgent,
        VisualizationAgent,
    ]:
        _registry.register(cls)


async def run_agent_task(request: AgentRunRequest) -> AgentRunResponse:
    """Main entry point: decompose, execute, and return results."""
    _ensure_agents_registered()
    tracker = get_tracker()
    bus = get_bus()
    memory = get_memory_store()

    task_id = str(int(time.time() * 1000))[-12:]
    agent_types = _registry.list_types()

    try:
        plan = decompose_task(
            task=request.task,
            context=request.context,
            available_agents=agent_types,
        )
        task_id = plan.task_id

        tracker.log(
            "info", "coordinator", task_id, f"Plan created: {len(plan.decomposed_steps)} steps"
        )

        # Store conversation in memory
        session_id = request.session_id or f"session_{task_id}"
        memory.add_conversation(session_id, "user", request.task, "user")

        # Execute the plan
        metrics = await run_plan(
            steps=plan.decomposed_steps,
            context={**request.context, "task_id": task_id, "session_id": session_id},
            task_id=task_id,
            max_retries=request.max_retries,
            timeout_seconds=request.timeout_seconds,
        )

        # Collect answer from last completed step
        answer = ""
        artifacts: list[dict[str, Any]] = []
        for step in plan.decomposed_steps:
            if step.status == "completed" and step.output_data:
                out = step.output_data
                if "output" in out:
                    answer = out["output"]
                if "artifacts" in out:
                    artifacts.extend(out["artifacts"])

        # Store result in memory
        memory.add_conversation(session_id, "assistant", answer, "coordinator")
        memory.add_task_memory(
            task_id,
            "coordinator",
            {
                "answer": answer[:500],
                "agents_used": plan.agent_sequence,
            },
        )

        # Record history
        tracker.record_task(
            task_id=task_id,
            task=request.task,
            agent_sequence=plan.agent_sequence,
            metrics=metrics,
            answer=answer,
        )

        tracker.log("info", "coordinator", task_id, "Task completed successfully")

        return AgentRunResponse(
            success=True,
            task_id=task_id,
            answer=answer,
            agent_sequence=plan.agent_sequence,
            steps=plan.decomposed_steps,
            metrics=metrics,
            artifacts=artifacts,
        )

    except Exception as exc:
        tracker.log("error", "coordinator", task_id, f"Task failed: {exc}")
        return AgentRunResponse(
            success=False,
            task_id=task_id,
            error=str(exc)[:500],
        )


def get_agent_list() -> AgentListResponse:
    """Get status of all registered agents."""
    _ensure_agents_registered()
    agents_data = _registry.list_all()
    agents = [
        AgentStatus(
            agent_type=a["agent_type"],
            name=a["name"],
            status=a["status"],
            tasks_completed=a["tasks_completed"],
            tasks_failed=a["tasks_failed"],
            avg_duration_ms=a["avg_duration_ms"],
            last_active=a["last_active"],
        )
        for a in agents_data
    ]
    return AgentListResponse(success=True, agents=agents, count=len(agents))


def get_task_history(limit: int = 50) -> TaskHistoryResponse:
    """Get execution task history."""
    tracker = get_tracker()
    tasks = tracker.get_task_history(limit=limit)
    return TaskHistoryResponse(success=True, tasks=tasks, count=len(tasks))


def get_agent_logs(
    task_id: str | None = None,
    agent_type: str | None = None,
    level: str | None = None,
    limit: int = 100,
) -> LogsResponse:
    """Get filtered agent logs."""
    tracker = get_tracker()
    logs = tracker.get_logs(task_id=task_id, agent_type=agent_type, level=level, limit=limit)
    return LogsResponse(success=True, logs=logs, count=len(logs))


def get_memory_entries(session_id: str | None = None, task_id: str | None = None) -> MemoryResponse:
    """Get memory entries."""
    memory = get_memory_store()
    entries: list[MemoryEntry] = []

    if session_id:
        conv = memory.get_conversation(session_id, limit=50)
        for c in conv:
            entries.append(
                MemoryEntry(
                    memory_type="conversation",
                    key=f"{session_id}:{c['id']}",
                    value=c.get("content", ""),
                    agent_type=c.get("agent_type", ""),
                    session_id=session_id,
                    created_at=time.strftime(
                        "%Y-%m-%dT%H:%M:%S", time.localtime(c.get("timestamp", 0))
                    ),
                )
            )

    if task_id:
        task_mem = memory.get_task_memory(task_id)
        for t in task_mem:
            entries.append(
                MemoryEntry(
                    memory_type="task",
                    key=f"{task_id}:{t['id']}",
                    value=t.get("data", {}),
                    agent_type=t.get("agent_type", ""),
                    task_id=task_id,
                    created_at=time.strftime(
                        "%Y-%m-%dT%H:%M:%S", time.localtime(t.get("timestamp", 0))
                    ),
                )
            )

    if not session_id and not task_id:
        shared = memory.get_all_shared()
        for k, v in shared.items():
            entries.append(
                MemoryEntry(
                    memory_type="shared",
                    key=k,
                    value=v,
                )
            )

    return MemoryResponse(success=True, entries=entries, count=len(entries))


def get_agent_metrics(agent_type: str | None = None) -> dict[str, Any]:
    """Get agent-level performance metrics."""
    tracker = get_tracker()
    return tracker.get_agent_metrics(agent_type)


def get_memory_stats() -> dict[str, Any]:
    """Get memory store stats."""
    return get_memory_store().get_stats()
