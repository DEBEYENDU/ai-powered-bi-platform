"""Workflow condition evaluation."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.workflows.schemas import ConditionOperator

log = get_logger("workflow.conditions")


def evaluate_condition(
    condition: dict[str, Any],
    results: dict[str, Any],
    input_data: dict[str, Any],
) -> bool:
    """Evaluate a single condition against current results and input."""
    metric = condition.get("metric", "")
    operator = condition.get("operator", "gt")
    value = condition.get("value")
    step_id = condition.get("step_id", "")

    # Resolve the actual value from results or input
    actual = _resolve_value(metric, step_id, results, input_data)

    if actual is None:
        log.warning("condition_value_not_found", metric=metric, step_id=step_id)
        return False

    return _compare(actual, operator, value)


def evaluate_conditions(
    conditions: list[dict[str, Any]],
    results: dict[str, Any],
    input_data: dict[str, Any],
) -> bool:
    """Evaluate all conditions. AND logic by default; OR if logical_op='OR'."""
    if not conditions:
        return True

    or_conditions: list[bool] = []
    and_conditions: list[bool] = []

    for cond in conditions:
        met = evaluate_condition(cond, results, input_data)
        if cond.get("logical_op", "AND") == "OR":
            or_conditions.append(met)
        else:
            and_conditions.append(met)

    # All AND conditions must be true
    and_result = all(and_conditions) if and_conditions else True
    # Any OR condition can be true
    or_result = any(or_conditions) if or_conditions else True

    return and_result and or_result


def _resolve_value(
    metric: str,
    step_id: str,
    results: dict[str, Any],
    input_data: dict[str, Any],
) -> Any:
    """Resolve a metric reference to its actual value."""
    # Check input data first
    if metric in input_data:
        return input_data[metric]

    # Check step results
    if step_id and step_id in results:
        step_result = results[step_id]
        if isinstance(step_result, dict) and metric in step_result:
            return step_result[metric]
        if isinstance(step_result, (int, float)):
            return step_result

    # Check top-level results for the metric
    for step_results in results.values():
        if isinstance(step_results, dict) and metric in step_results:
            return step_results[metric]

    # Check nested output_data
    for step_results in results.values():
        if isinstance(step_results, dict):
            output = step_results.get("output_data", {})
            if isinstance(output, dict) and metric in output:
                return output[metric]

    return None


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    """Compare actual vs expected using the given operator."""
    try:
        if operator == ConditionOperator.GT:
            return float(actual) > float(expected)
        if operator == ConditionOperator.GTE:
            return float(actual) >= float(expected)
        if operator == ConditionOperator.LT:
            return float(actual) < float(expected)
        if operator == ConditionOperator.LTE:
            return float(actual) <= float(expected)
        if operator == ConditionOperator.EQ:
            return str(actual) == str(expected)
        if operator == ConditionOperator.NEQ:
            return str(actual) != str(expected)
        if operator == ConditionOperator.CONTAINS:
            return str(expected).lower() in str(actual).lower()
        if operator == ConditionOperator.NOT_CONTAINS:
            return str(expected).lower() not in str(actual).lower()
        if operator == ConditionOperator.IN:
            if isinstance(expected, list):
                return actual in expected
            return str(actual) in str(expected)
        if operator == ConditionOperator.NOT_IN:
            if isinstance(expected, list):
                return actual not in expected
            return str(actual) not in str(expected)
    except (TypeError, ValueError):
        return False
    return False
