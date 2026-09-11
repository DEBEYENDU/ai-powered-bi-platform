"""Agent task runner with retries, timeouts, and step tracking."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.ai.agents.monitoring.tracker import get_tracker
from app.ai.agents.registry.agent_registry import get_registry
from app.ai.agents.schemas import ExecutionMetrics, TaskStep


async def _run_single_step(
    step: TaskStep,
    context: dict[str, Any],
    timeout_seconds: int,
) -> TaskStep:
    """Execute a single agent step with timeout and error handling."""
    registry = get_registry()
    tracker = get_tracker()

    if not registry.has(step.agent_type):
        step.status = "failed"
        step.error = f"Agent '{step.agent_type}' not registered"
        return step

    agent = registry.get(step.agent_type)
    step.status = "running"
    step.started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    tracker.log("info", step.agent_type, step.step_id, f"Starting {step.agent_type} agent")

    t0 = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            agent.execute(
                task=step.input_data.get("task", ""),
                context={**context, **step.input_data},
                tools=None,
            ),
            timeout=timeout_seconds,
        )
        duration = (time.perf_counter() - t0) * 1000

        step.output_data = result
        step.status = "completed"
        step.completed_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        step.duration_ms = round(duration, 1)

        registry.record_success(step.agent_type, duration)
        tracker.log(
            "info",
            step.agent_type,
            step.step_id,
            f"Completed in {duration:.0f}ms",
            {"output_keys": list(result.keys())},
        )
    except TimeoutError:
        duration = (time.perf_counter() - t0) * 1000
        step.status = "failed"
        step.error = f"Timeout after {timeout_seconds}s"
        step.duration_ms = round(duration, 1)
        registry.record_failure(step.agent_type)
        tracker.log("error", step.agent_type, step.step_id, step.error)
    except Exception as exc:
        duration = (time.perf_counter() - t0) * 1000
        step.status = "failed"
        step.error = str(exc)[:500]
        step.duration_ms = round(duration, 1)
        registry.record_failure(step.agent_type)
        tracker.log("error", step.agent_type, step.step_id, f"Error: {exc}")

    return step


async def run_plan(
    steps: list[TaskStep],
    context: dict[str, Any],
    task_id: str,
    max_retries: int = 2,
    timeout_seconds: int = 120,
) -> ExecutionMetrics:
    """Execute a list of steps sequentially, with retries on failure."""
    tracker = get_tracker()
    tracker.log("info", "runner", task_id, f"Executing plan with {len(steps)} steps")

    total_duration = 0.0
    failures = 0
    retries = 0

    for step in steps:
        # Gather outputs from prior steps as additional context
        for prev in steps:
            if prev.step_id in (step.input_data.get("dependencies", [])) and prev.output_data:
                step.input_data[f"prior_{prev.agent_type}"] = prev.output_data

        attempt = 0
        while attempt <= max_retries:
            step.retries = attempt
            step = await _run_single_step(step, context, timeout_seconds)
            if step.status == "completed":
                break
            attempt += 1
            if attempt <= max_retries:
                retries += 1
                tracker.log("warning", step.agent_type, task_id, f"Retry {attempt}/{max_retries}")
                await asyncio.sleep(min(attempt * 0.5, 3.0))

        total_duration += step.duration_ms
        if step.status == "failed":
            failures += 1

    completed = sum(1 for s in steps if s.status == "completed")

    return ExecutionMetrics(
        task_id=task_id,
        total_duration_ms=round(total_duration, 1),
        agents_called=completed,
        failures=failures,
        retries=retries,
        steps=steps,
    )
