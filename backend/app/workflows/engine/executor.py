"""Core workflow execution engine."""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any

from app.core.logging import get_logger
from app.workflows.schemas import (
    ActionType,
    ExecutionStatus,
    StepDefinition,
    StepStatus,
)

log = get_logger("workflow.engine")

# Dangerous SQL keywords that require explicit approval
_DANGEROUS_SQL = {"DROP", "DELETE", "TRUNCATE", "ALTER", "RENAME", "REPLACE"}


class WorkflowEngine:
    """Executes workflow steps sequentially or in parallel, with retries and fallbacks."""

    async def execute_workflow(
        self,
        workflow_id: str,
        steps: list[StepDefinition],
        conditions: list[dict[str, Any]],
        input_data: dict[str, Any],
        max_retries: int = 3,
        timeout_seconds: int = 3600,
        is_test: bool = False,
        organization_id: str = "",
    ) -> dict[str, Any]:
        """Execute a complete workflow and return the execution result."""
        execution_id = str(uuid.uuid4())[:12]
        start = time.perf_counter()
        results: dict[str, Any] = {}
        step_executions: list[dict[str, Any]] = []
        errors: list[str] = []

        log.info(
            "workflow_started",
            workflow_id=workflow_id,
            execution_id=execution_id,
            steps=len(steps),
            is_test=is_test,
        )

        # Group steps by dependency level
        levels = self._resolve_dependency_levels(steps)

        for level_idx, level_steps in enumerate(levels):
            # Check conditions before executing this level
            if conditions:
                condition_met = await self._evaluate_conditions(conditions, results, input_data)
                if not condition_met:
                    log.info("conditions_not_met", level=level_idx)
                    break

            # Execute steps at this level (may be parallel)
            if len(level_steps) == 1:
                step = level_steps[0]
                result = await self._execute_step(
                    step, results, input_data, max_retries, is_test, organization_id
                )
                step_executions.append(result)
                results[step.id] = result.get("output_data", {})
                if result["status"] == StepStatus.FAILED and not step.continue_on_failure:
                    errors.append(f"Step {step.name} failed: {result.get('error', '')}")
                    break
            else:
                # Parallel execution
                parallel_results = await asyncio.gather(
                    *[
                        self._execute_step(
                            step, results, input_data, max_retries, is_test, organization_id
                        )
                        for step in level_steps
                    ],
                    return_exceptions=True,
                )
                for i, result in enumerate(parallel_results):
                    if isinstance(result, Exception):
                        step = level_steps[i]
                        step_executions.append(
                            {
                                "step_id": step.id,
                                "step_name": step.name,
                                "status": StepStatus.FAILED,
                                "error": str(result),
                            }
                        )
                        errors.append(f"Step {step.name} failed: {result}")
                        results[step.id] = {}
                    else:
                        step_executions.append(result)
                        results[result["step_id"]] = result.get("output_data", {})

        duration_ms = (time.perf_counter() - start) * 1000
        status = ExecutionStatus.COMPLETED if not errors else ExecutionStatus.FAILED

        log.info(
            "workflow_completed",
            workflow_id=workflow_id,
            execution_id=execution_id,
            status=status,
            duration_ms=round(duration_ms, 1),
        )

        return {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": status,
            "output_data": results,
            "errors": errors,
            "steps": step_executions,
            "duration_ms": round(duration_ms, 1),
            "started_at": datetime.utcnow().isoformat(),
        }

    def _resolve_dependency_levels(self, steps: list[StepDefinition]) -> list[list[StepDefinition]]:
        """Resolve steps into dependency levels for sequential/parallel execution."""
        placed: set[str] = set()
        levels: list[list[StepDefinition]] = []

        remaining = list(steps)
        max_iterations = len(steps) + 1
        iterations = 0

        while remaining and iterations < max_iterations:
            iterations += 1
            level: list[StepDefinition] = []
            still_remaining: list[StepDefinition] = []

            for step in remaining:
                deps = set(step.depends_on) - placed
                if not deps:
                    level.append(step)
                else:
                    still_remaining.append(step)

            if not level:
                # Circular dependency fallback — execute remaining sequentially
                level = still_remaining[:1]
                still_remaining = still_remaining[1:]

            for s in level:
                placed.add(s.id)
            levels.append(level)
            remaining = still_remaining

        return levels

    async def _execute_step(
        self,
        step: StepDefinition,
        prior_results: dict[str, Any],
        input_data: dict[str, Any],
        max_retries: int,
        is_test: bool,
        organization_id: str,
    ) -> dict[str, Any]:
        """Execute a single step with retries."""
        start = time.perf_counter()
        last_error = ""

        # Validate dangerous actions
        if step.action_type in (ActionType.RUN_SQL,) and self._is_dangerous_action(step.config):
            return {
                "step_id": step.id,
                "step_name": step.name,
                "action_type": step.action_type,
                "status": StepStatus.FAILED,
                "error": "Dangerous SQL operation requires explicit admin approval",
                "duration_ms": 0,
            }

        # Check if approval is required
        if step.is_approval_required:
            return {
                "step_id": step.id,
                "step_name": step.name,
                "action_type": step.action_type,
                "status": StepStatus.WAITING_APPROVAL,
                "requires_approval": True,
                "assigned_to": step.approval_assigned_to,
                "duration_ms": 0,
            }

        for attempt in range(max_retries + 1):
            try:
                result = await self._run_action(
                    step.action_type, step.config, prior_results, input_data, is_test
                )
                duration = (time.perf_counter() - start) * 1000

                return {
                    "step_id": step.id,
                    "step_name": step.name,
                    "action_type": step.action_type,
                    "status": StepStatus.COMPLETED,
                    "output_data": result,
                    "duration_ms": round(duration, 1),
                    "retry_count": attempt,
                }
            except Exception as exc:
                last_error = str(exc)
                log.warning(
                    "step_failed",
                    step_id=step.id,
                    attempt=attempt,
                    error=last_error,
                )
                if attempt < max_retries:
                    backoff = min(2**attempt, 30)
                    await asyncio.sleep(backoff)

        duration = (time.perf_counter() - start) * 1000

        # Try fallback step if configured
        if step.fallback_step_id and step.fallback_step_id in {s.id for s in []}:
            log.info("trying_fallback", step_id=step.id, fallback=step.fallback_step_id)

        return {
            "step_id": step.id,
            "step_name": step.name,
            "action_type": step.action_type,
            "status": StepStatus.FAILED,
            "error": last_error,
            "duration_ms": round(duration, 1),
            "retry_count": max_retries,
        }

    async def _run_action(
        self,
        action_type: ActionType,
        config: dict[str, Any],
        prior_results: dict[str, Any],
        input_data: dict[str, Any],
        is_test: bool,
    ) -> dict[str, Any]:
        """Dispatch to the appropriate action handler."""
        from app.workflows.actions.registry import get_action_handler

        handler = get_action_handler(action_type)
        return await handler.execute(config, prior_results, input_data, is_test)

    async def _evaluate_conditions(
        self,
        conditions: list[dict[str, Any]],
        results: dict[str, Any],
        input_data: dict[str, Any],
    ) -> bool:
        """Evaluate all conditions. All must be true (AND logic by default)."""
        from app.workflows.conditions.evaluator import evaluate_conditions

        return evaluate_conditions(conditions, results, input_data)

    def _is_dangerous_action(self, config: dict[str, Any]) -> bool:
        """Check if a SQL action contains dangerous operations."""
        query = config.get("query", "").upper()
        return any(kw in query for kw in _DANGEROUS_SQL)


# Singleton
_engine: WorkflowEngine | None = None


def get_engine() -> WorkflowEngine:
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
