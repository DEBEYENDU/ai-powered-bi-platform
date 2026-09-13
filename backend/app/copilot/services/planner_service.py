from __future__ import annotations

import json

from app.ai.providers.base import ChatMessage
from app.ai.providers.registry import get_provider
from app.copilot.schemas.plan import ExecutionPlan, IntentResult, PlanStep
from app.copilot.tools.registry import ToolRegistry
from app.core.config import get_settings

PLANNER_SYSTEM_PROMPT = """You are a task planner for a Business Intelligence platform.
Given a user request and the intent, create a structured execution plan.

Available tools:
- sql_query: Execute natural language queries against the database
- rag_query: Search enterprise knowledge base (policies, documents)
- dashboard_generator: Create interactive dashboards
- report_generator: Generate business reports
- forecast: Generate forecasts for metrics
- business_analysis: Analyze KPIs, trends, anomalies
- data_profile: Profile datasets for structure and quality
- workflow_generator: Create automated workflows
- notification: Send notifications

Respond with ONLY a JSON object:
{
    "goal": "brief description of what we're doing",
    "steps": [
        {
            "id": "step_1",
            "tool": "tool_name",
            "purpose": "what this step does",
            "params": {},
            "depends_on": [],
            "risk_level": "low"
        }
    ],
    "requires_clarification": false,
    "clarification_question": null,
    "risk_assessment": "low|medium|high"
}

Rules:
- Each step must use an available tool
- Steps that depend on others must list their step IDs in depends_on
- Never create circular dependencies
- For knowledge questions, use rag_query
- For data questions, use sql_query
- For analysis, use business_analysis
- For dashboards, use dashboard_generator
- For reports, use report_generator
- For forecasts, use forecast
- For mixed questions, create multiple steps
- Keep steps minimal - don't over-plan
"""


class PlannerService:
    def __init__(self):
        self.settings = get_settings()
        self.tool_registry = ToolRegistry.get_instance()

    async def create_plan(
        self, query: str, intent: IntentResult, context: dict | None = None
    ) -> ExecutionPlan:
        """Create an execution plan using the LLM."""
        provider = get_provider()
        model = self.settings.ai_model

        tools_desc = "\n".join(
            f"- {t['name']}: {t['description']} (risk: {t['risk_level']})"
            for t in self.tool_registry.list_tools()
        )

        user_prompt = f"""User request: {query}
Detected intent: {intent.intent} (confidence: {intent.confidence})
Entities: {json.dumps(intent.entities)}
Available tools:
{tools_desc}

Create an execution plan."""

        messages = [
            ChatMessage(role="system", content=PLANNER_SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_prompt),
        ]

        try:
            response = await provider.chat(messages, model=model, temperature=0.2, max_tokens=1500)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            plan_data = json.loads(content)

            steps = []
            for s in plan_data.get("steps", []):
                steps.append(
                    PlanStep(
                        id=s.get("id", f"step_{len(steps) + 1}"),
                        tool=s.get("tool", "sql_query"),
                        purpose=s.get("purpose", ""),
                        params=s.get("params", {}),
                        depends_on=s.get("depends_on", []),
                        risk_level=s.get("risk_level", "low"),
                    )
                )

            return ExecutionPlan(
                goal=plan_data.get("goal", query),
                steps=steps,
                requires_clarification=plan_data.get("requires_clarification", False),
                clarification_question=plan_data.get("clarification_question"),
                risk_assessment=plan_data.get("risk_assessment", "low"),
            )
        except Exception:
            return self._fallback_plan(query, intent)

    def _fallback_plan(self, query: str, intent: IntentResult) -> ExecutionPlan:
        """Create a simple plan when LLM planning fails."""
        intent_to_tool = {
            "data_query": "sql_query",
            "data_analysis": "business_analysis",
            "dashboard_creation": "dashboard_generator",
            "report_generation": "report_generator",
            "forecasting": "forecast",
            "knowledge_search": "rag_query",
            "comparison": "sql_query",
            "anomaly_analysis": "business_analysis",
            "data_quality": "data_profile",
            "workflow_creation": "workflow_generator",
        }

        tool = intent_to_tool.get(intent.intent, "sql_query")
        steps = [
            PlanStep(
                id="step_1",
                tool=tool,
                purpose=f"Execute {intent.intent}",
                params={"question": query},
            )
        ]

        if intent.intent in ("data_analysis", "comparison", "anomaly_analysis"):
            steps.append(
                PlanStep(
                    id="step_2",
                    tool="business_analysis",
                    purpose="Analyze results",
                    depends_on=["step_1"],
                )
            )

        return ExecutionPlan(goal=query, steps=steps, risk_assessment="low")
