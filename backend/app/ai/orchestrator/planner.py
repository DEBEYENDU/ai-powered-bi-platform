"""Task planner for AI Business Assistant."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    step_id: str
    tool_name: str
    description: str
    dependencies: list[str] = Field(default_factory=list)
    input_source: str | None = Field(None, description="Where to get input from")
    parallel_group: str | None = Field(None, description="Group for parallel execution")
    timeout: float = 30.0
    retry_count: int = 0


class ExecutionPlan(BaseModel):
    plan_id: str
    steps: list[PlanStep]
    estimated_time: float
    confidence: float

    def get_parallel_groups(self) -> dict[str, list[PlanStep]]:
        groups: dict[str, list[PlanStep]] = {}
        for step in self.steps:
            if step.parallel_group:
                groups.setdefault(step.parallel_group, []).append(step)
        return groups

    def get_ordered_steps(self) -> list[PlanStep]:
        ordered: list[PlanStep] = []
        seen: set = set()
        for step in self.steps:
            if step.step_id not in seen:
                ordered.append(step)
                seen.add(step.step_id)
        return ordered


class Planner(BaseModel):
    def create_plan(
        self,
        intent_detection: Any,
        available_tools: list[str],
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        tools = (
            intent_detection.suggested_tools if hasattr(intent_detection, "suggested_tools") else []
        )
        entities = intent_detection.entities if hasattr(intent_detection, "entities") else {}
        confidence = intent_detection.confidence if hasattr(intent_detection, "confidence") else 0.5

        steps: list[PlanStep] = []
        step_counter = 0
        parallel_group = f"group_{step_counter}"

        for tool_name in tools:
            step_counter += 1
            step_id = f"step_{step_counter}"
            desc = self._describe_tool(tool_name, entities)
            steps.append(
                PlanStep(
                    step_id=step_id,
                    tool_name=tool_name,
                    description=desc,
                    dependencies=[],
                    parallel_group=parallel_group,
                )
            )

        plan_id = f"plan_{hash(str(tools)) % 100000}"
        return ExecutionPlan(
            plan_id=plan_id,
            steps=steps,
            estimated_time=len(steps) * 5.0,
            confidence=confidence,
        )

    def _describe_tool(self, tool_name: str, entities: dict[str, Any]) -> str:
        return f"Execute {tool_name} with entities: {entities}"
