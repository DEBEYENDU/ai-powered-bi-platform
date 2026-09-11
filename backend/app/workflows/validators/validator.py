"""Workflow validation."""

from __future__ import annotations

from typing import Any

from app.workflows.schemas import ActionType, StepDefinition, TriggerConfig, TriggerType

# Actions that require a query or dataset
_DATA_ACTIONS = {ActionType.RUN_SQL, ActionType.ANALYZE_DATASET, ActionType.GENERATE_FORECAST}


def validate_workflow(
    name: str,
    steps: list[StepDefinition],
    trigger: TriggerConfig,
    conditions: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Validate a workflow definition. Returns list of error messages (empty = valid)."""
    errors: list[str] = []

    if not name or not name.strip():
        errors.append("Workflow name is required")

    if not steps:
        errors.append("Workflow must have at least one step")

    # Validate trigger
    if trigger.type == TriggerType.CRON and not trigger.cron_expression:
        errors.append("Cron expression is required for cron triggers")

    # Validate steps
    step_ids: set[str] = set()
    for i, step in enumerate(steps):
        if not step.name:
            errors.append(f"Step {i + 1}: name is required")
        if step.id in step_ids:
            errors.append(f"Step {i + 1}: duplicate step ID '{step.id}'")
        step_ids.add(step.id)

        # Validate dependencies exist
        for dep_id in step.depends_on:
            if dep_id not in step_ids and dep_id not in {s.id for s in steps[:i]}:
                errors.append(f"Step '{step.name}': depends on unknown step '{dep_id}'")

        # Validate data actions have required config
        if step.action_type in _DATA_ACTIONS:
            if step.action_type == ActionType.RUN_SQL and not step.config.get("query"):
                errors.append(f"Step '{step.name}': SQL query is required")
            if step.action_type == ActionType.ANALYZE_DATASET and not step.config.get("dataset_id"):
                errors.append(f"Step '{step.name}': dataset_id is required")

        # Validate email action
        if step.action_type == ActionType.SEND_EMAIL:
            if not step.config.get("to"):
                errors.append(f"Step '{step.name}': email recipient is required")
            if not step.config.get("subject"):
                errors.append(f"Step '{step.name}': email subject is required")

    # Check for circular dependencies
    if _has_cycle(steps):
        errors.append("Workflow contains circular dependencies")

    # Validate conditions reference valid steps or metrics
    for cond in conditions or []:
        step_ref = cond.get("step_id", "")
        if step_ref and step_ref not in step_ids:
            errors.append(f"Condition references unknown step '{step_ref}'")

    return errors


def _has_cycle(steps: list[StepDefinition]) -> bool:
    """Detect cycles in step dependencies using DFS."""
    graph: dict[str, list[str]] = {s.id: list(s.depends_on) for s in steps}
    visited: set[str] = set()
    in_stack: set[str] = set()

    def dfs(node: str) -> bool:
        if node in in_stack:
            return True
        if node in visited:
            return False
        visited.add(node)
        in_stack.add(node)
        for dep in graph.get(node, []):
            if dfs(dep):
                return True
        in_stack.discard(node)
        return False

    return any(dfs(sid) for sid in graph if sid not in visited)
