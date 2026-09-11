"""AI workflow builder — generates structured workflows from natural language."""

from __future__ import annotations

import json
from typing import Any

from app.core.logging import get_logger

log = get_logger("workflow.ai")

_WORKFLOW_BUILDER_PROMPT = """\
You are a workflow automation expert. Convert the user's natural language request
into a structured workflow JSON.

Available trigger types: manual, scheduled, cron, daily, weekly, monthly, quarterly
Available action types: run_sql, analyze_dataset, generate_dashboard, generate_report,
  generate_forecast, run_ai_agent, send_email, send_notification, create_alert,
  export_pdf, export_excel, export_powerpoint, save_file, call_webhook, run_pipeline,
  human_approval, evaluate_condition
Available condition operators: gt, gte, lt, lt, eq, neq, contains, not_contains, in, not_in

Return ONLY valid JSON with this structure:
{
  "name": "workflow name",
  "description": "what it does",
  "trigger": { "type": "...", "time": "...", "day_of_week": "...", "day_of_month": ..., "cron_expression": "..." },
  "steps": [
    {
      "id": "step_1",
      "name": "...",
      "action_type": "...",
      "config": { ... },
      "depends_on": []
    }
  ],
  "conditions": [
    { "metric": "...", "operator": "...", "value": ..., "step_id": "..." }
  ],
  "tags": ["..."]
}

Rules:
- Steps should use sequential IDs (step_1, step_2, etc.)
- Each step's depends_on should reference prior step IDs
- Conditions should reference step_ids from the workflow
- The last step should usually be a notification
- Do NOT execute the workflow, just generate the structure
"""


async def generate_workflow(prompt: str) -> dict[str, Any]:
    """Generate a workflow structure from natural language using LLM."""
    try:
        from app.ai.providers.registry import get_provider

        llm = get_provider()
        messages = [
            {"role": "system", "content": _WORKFLOW_BUILDER_PROMPT},
            {"role": "user", "content": prompt},
        ]

        raw = await llm.chat_completion(
            messages=messages,
            temperature=0.2,
            max_tokens=3000,
        )

        # Extract text from response
        text = ""
        if isinstance(raw, str):
            text = raw
        elif isinstance(raw, dict) and "choices" in raw:
            text = raw["choices"][0].get("message", {}).get("content", "")
        elif hasattr(raw, "choices"):
            text = raw.choices[0].message.content or ""

        # Parse JSON from response
        workflow = _extract_json(text)
        if workflow:
            # Validate and normalize
            workflow = _normalize_workflow(workflow)
            return {"success": True, "workflow": workflow}

        return {"success": False, "error": "Could not parse AI response into workflow structure"}

    except Exception as exc:
        log.error("ai_workflow_generation_failed", error=str(exc))
        return {"success": False, "error": str(exc)}


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract JSON from LLM response text."""
    # Try to find JSON block
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()

    # Find first { to last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1:
        text = text[first_brace : last_brace + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _normalize_workflow(wf: dict[str, Any]) -> dict[str, Any]:
    """Normalize and validate the AI-generated workflow structure."""
    # Ensure required fields
    wf.setdefault("name", "AI-Generated Workflow")
    wf.setdefault("description", "")
    wf.setdefault("steps", [])
    wf.setdefault("conditions", [])
    wf.setdefault("tags", ["ai-generated"])

    # Normalize trigger
    trigger = wf.get("trigger", {})
    if isinstance(trigger, str):
        trigger = {"type": trigger}
    wf["trigger"] = _normalize_trigger(trigger)

    # Normalize steps
    normalized_steps = []
    for i, step in enumerate(wf["steps"]):
        step_id = step.get("id", f"step_{i + 1}")
        normalized_steps.append(
            {
                "id": step_id,
                "name": step.get("name", f"Step {i + 1}"),
                "action_type": step.get("action_type", "run_sql"),
                "config": step.get("config", {}),
                "depends_on": step.get("depends_on", []),
                "retry_on_failure": step.get("retry_on_failure", True),
                "max_retries": step.get("max_retries", 3),
                "timeout_seconds": step.get("timeout_seconds", 300),
                "continue_on_failure": step.get("continue_on_failure", False),
                "is_approval_required": step.get("is_approval_required", False),
            }
        )
    wf["steps"] = normalized_steps

    # Normalize conditions
    normalized_conditions = []
    for cond in wf.get("conditions", []):
        normalized_conditions.append(
            {
                "id": cond.get("id", f"cond_{len(normalized_conditions) + 1}"),
                "metric": cond.get("metric", ""),
                "operator": cond.get("operator", "gt"),
                "value": cond.get("value"),
                "step_id": cond.get("step_id", ""),
                "description": cond.get("description", ""),
            }
        )
    wf["conditions"] = normalized_conditions

    return wf


def _normalize_trigger(trigger: dict[str, Any]) -> dict[str, Any]:
    """Normalize trigger configuration."""
    trigger_type = trigger.get("type", "manual")
    normalized = {"type": trigger_type}

    if trigger_type == "cron":
        normalized["cron_expression"] = trigger.get("cron_expression", "")
    elif trigger_type in ("daily", "scheduled"):
        normalized["time"] = trigger.get("time", "09:00")
    elif trigger_type == "weekly":
        normalized["day_of_week"] = trigger.get("day_of_week", "monday")
        normalized["time"] = trigger.get("time", "09:00")
    elif trigger_type in ("monthly", "quarterly"):
        normalized["day_of_month"] = trigger.get("day_of_month", 1)
        normalized["time"] = trigger.get("time", "09:00")

    return normalized
