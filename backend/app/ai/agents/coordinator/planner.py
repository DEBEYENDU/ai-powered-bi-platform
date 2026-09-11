"""Task decomposition and execution planning."""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.ai.agents.prompts.templates import PLANNER_DECOMPOSE
from app.ai.agents.schemas import ExecutionPlan, TaskStep

# Mapping of intent keywords to agent types
_INTENT_MAP: dict[str, list[str]] = {
    "sql": ["sql"],
    "query": ["sql"],
    "database": ["sql"],
    "dashboard": ["dashboard", "visualization"],
    "chart": ["visualization"],
    "kpi": ["business_analyst"],
    "trend": ["business_analyst"],
    "anomal": ["business_analyst"],
    "forecast": ["forecast"],
    "predict": ["forecast"],
    "revenue": ["forecast", "business_analyst"],
    "report": ["report"],
    "executive": ["report"],
    "summary": ["report"],
    "quality": ["data_quality"],
    "clean": ["data_quality"],
    "valid": ["data_quality"],
    "security": ["security"],
    "permission": ["security"],
    "audit": ["security"],
    "workflow": ["workflow"],
    "schedule": ["workflow"],
    "automat": ["workflow"],
    "search": ["knowledge"],
    "document": ["knowledge"],
    "policy": ["knowledge"],
    "visual": ["visualization"],
    "layout": ["visualization"],
}


def _detect_intent(task: str) -> list[str]:
    """Detect which agents are needed from the task description."""
    task_lower = task.lower()
    needed: list[str] = []
    seen: set[str] = set()
    for keyword, agents in _INTENT_MAP.items():
        if keyword in task_lower:
            for agent in agents:
                if agent not in seen:
                    needed.append(agent)
                    seen.add(agent)
    if not needed:
        needed = ["business_analyst"]
    return needed


def _build_steps(task: str, agent_types: list[str], context: dict[str, Any]) -> list[TaskStep]:
    """Build execution steps from detected agent types."""
    steps: list[TaskStep] = []
    for idx, agent_type in enumerate(agent_types):
        deps = [steps[idx - 1].step_id] if idx > 0 else []
        step = TaskStep(
            step_id=str(uuid.uuid4())[:12],
            agent_type=agent_type,
            description=f"Execute {agent_type} agent for: {task[:100]}",
            input_data={"task": task, "context": context, "dependencies": deps},
            status="pending",
        )
        steps.append(step)
    return steps


def decompose_task(
    task: str,
    context: dict[str, Any],
    available_agents: list[str] | None = None,
) -> ExecutionPlan:
    """Decompose a user task into an execution plan.

    Uses rule-based intent detection to select agents and build a plan.
    Falls back to a simple single-step plan if detection yields nothing useful.
    """
    agent_types = _detect_intent(task)

    if available_agents:
        agent_types = [a for a in agent_types if a in available_agents]
    if not agent_types:
        agent_types = ["business_analyst"]

    steps = _build_steps(task, agent_types, context)
    estimated = len(steps) * 5000.0  # ~5s per step estimate

    return ExecutionPlan(
        task_id=str(uuid.uuid4())[:12],
        original_task=task,
        decomposed_steps=steps,
        agent_sequence=agent_types,
        estimated_duration_ms=estimated,
    )


def decompose_task_llm(
    task: str,
    context: dict[str, Any],
    available_agents: list[str],
    agent_capabilities: str = "",
) -> ExecutionPlan:
    """Use LLM to decompose a complex task. Falls back to rule-based on failure."""
    try:
        from app.ai.providers.registry import get_provider

        llm = get_provider()
        prompt = PLANNER_DECOMPOSE.format(
            task=task,
            context=json.dumps(context, default=str)[:2000],
            agent_capabilities=agent_capabilities or "\n".join(available_agents),
        )
        # This is a placeholder for async LLM call — orchestrator will handle the actual call
        return decompose_task(task, context, available_agents)
    except Exception:
        return decompose_task(task, context, available_agents)
