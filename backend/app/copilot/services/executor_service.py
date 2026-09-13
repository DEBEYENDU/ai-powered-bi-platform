from __future__ import annotations

import time

from app.copilot.schemas.plan import ExecutionPlan, PlanStep
from app.copilot.schemas.response import CopilotStepResult
from app.copilot.tools.registry import ToolRegistry
from app.core.logging import get_logger

log = get_logger("copilot.executor")


class ExecutionEngine:
    def __init__(self):
        self.tool_registry = ToolRegistry.get_instance()

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        context: dict,
        on_step_complete: callable | None = None,
    ) -> tuple[list[CopilotStepResult], list[str]]:
        """Execute a plan step by step, respecting dependencies.
        Returns (step_results, tools_used)."""

        results: dict[str, CopilotStepResult] = {}
        tools_used: list[str] = []
        completed: set[str] = set()

        pending = {s.id: s for s in plan.steps}

        max_iterations = len(plan.steps) + 1
        iteration = 0

        while pending and iteration < max_iterations:
            iteration += 1

            ready = []
            for _step_id, step in pending.items():
                deps_met = all(d in completed for d in step.depends_on)
                if deps_met:
                    ready.append(step)

            if not ready:
                for step_id in list(pending.keys()):
                    results[step_id] = CopilotStepResult(
                        step_id=step_id,
                        tool_name=pending[step_id].tool,
                        purpose=pending[step_id].purpose,
                        status="skipped",
                        error="Dependency not met",
                    )
                    del pending[step_id]
                break

            for step in ready:
                step_result = await self._execute_step(step, context, results)
                results[step.id] = step_result
                tools_used.append(step.tool)
                completed.add(step.id)
                del pending[step.id]

                if on_step_complete:
                    on_step_complete(step_result)

        step_list = [results[s.id] for s in plan.steps if s.id in results]
        return step_list, tools_used

    async def _execute_step(
        self,
        step: PlanStep,
        context: dict,
        prior_results: dict[str, CopilotStepResult],
    ) -> CopilotStepResult:
        """Execute a single step."""
        start = time.time()

        tool = self.tool_registry.get(step.tool)
        if tool is None:
            return CopilotStepResult(
                step_id=step.id,
                tool_name=step.tool,
                purpose=step.purpose,
                status="failed",
                error=f"Unknown tool: {step.tool}",
                duration_ms=(time.time() - start) * 1000,
            )

        params = dict(step.params)
        for dep_id in step.depends_on:
            dep_result = prior_results.get(dep_id)
            if dep_result and dep_result.result:
                params[f"_{dep_id}_result"] = dep_result.result

        exec_context = dict(context)
        exec_context["prior_results"] = {k: v.result for k, v in prior_results.items()}

        try:
            result = await tool.execute(params, exec_context)
            return CopilotStepResult(
                step_id=step.id,
                tool_name=step.tool,
                purpose=step.purpose,
                status="completed",
                result=result,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as exc:
            log.error(
                "step_execution_failed step=%s tool=%s error=%s", step.id, step.tool, str(exc)
            )
            return CopilotStepResult(
                step_id=step.id,
                tool_name=step.tool,
                purpose=step.purpose,
                status="failed",
                error=str(exc),
                duration_ms=(time.time() - start) * 1000,
            )
