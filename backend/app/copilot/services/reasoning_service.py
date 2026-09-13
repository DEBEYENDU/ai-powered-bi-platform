from __future__ import annotations

import json

from app.ai.providers.base import ChatMessage
from app.ai.providers.registry import get_provider
from app.copilot.schemas.plan import ExecutionPlan
from app.copilot.schemas.response import CopilotStepResult
from app.core.config import get_settings

REASONING_SYSTEM_PROMPT = """You are a business analyst AI that converts raw data results into clear, actionable business insights.

Given tool execution results and the original user request, provide:
1. A clear, concise answer to the user's question
2. Key findings with evidence
3. Any caveats or limitations

Rules:
- Base your answer ONLY on the actual tool results provided
- Never fabricate data, numbers, or sources
- If data is insufficient, say so clearly
- Use bullet points for key findings
- Include specific numbers from the data when available
- If there are multiple data sources, synthesize them
- Cite which tool/steps provided each piece of information

Respond with a JSON object:
{
    "answer": "clear business answer in markdown",
    "key_findings": ["finding 1", "finding 2"],
    "data_sources": ["step_1: sql_query", "step_2: business_analysis"],
    "caveats": ["any limitations"],
    "confidence": 0.0 to 1.0
}
"""


class ReasoningService:
    def __init__(self):
        self.settings = get_settings()

    async def reason(
        self,
        query: str,
        plan: ExecutionPlan,
        step_results: list[CopilotStepResult],
    ) -> dict:
        """Generate business reasoning from tool results."""
        provider = get_provider()
        model = self.settings.ai_model

        results_context = []
        for sr in step_results:
            if sr.status == "completed" and sr.result:
                data = sr.result.get("data", sr.result)
                if isinstance(data, dict):
                    if "rows" in data:
                        summary = f"Rows: {data.get('row_count', len(data['rows']))}, Columns: {data.get('columns', [])}"
                    elif "answer" in data:
                        summary = data["answer"][:500]
                    elif "summary" in data:
                        summary = str(data["summary"])[:500]
                    else:
                        summary = json.dumps(data, default=str)[:500]
                else:
                    summary = str(data)[:500]
                results_context.append(f"Step {sr.step_id} ({sr.tool_name}): {summary}")
            elif sr.status == "failed":
                results_context.append(f"Step {sr.step_id} ({sr.tool_name}): FAILED - {sr.error}")

        user_prompt = f"""User request: {query}

Execution plan goal: {plan.goal}

Tool results:
{chr(10).join(results_context)}

Provide a business insight answer."""

        messages = [
            ChatMessage(role="system", content=REASONING_SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_prompt),
        ]

        try:
            response = await provider.chat(messages, model=model, temperature=0.3, max_tokens=2000)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return json.loads(content)
        except Exception:
            return self._fallback_reasoning(query, step_results)

    def _fallback_reasoning(self, query: str, step_results: list[CopilotStepResult]) -> dict:
        """Simple fallback when LLM reasoning fails."""
        parts = []
        sources = []
        for sr in step_results:
            if sr.status == "completed" and sr.result:
                data = sr.result.get("data", sr.result)
                if isinstance(data, dict):
                    if "answer" in data:
                        parts.append(data["answer"])
                    elif "explanation" in data:
                        parts.append(data["explanation"])
                    elif "rows" in data:
                        parts.append(f"Query returned {data.get('row_count', 0)} rows.")
                sources.append(f"{sr.step_id}: {sr.tool_name}")

        answer = "\n\n".join(parts) if parts else "Analysis completed but no summary available."

        return {
            "answer": answer,
            "key_findings": [],
            "data_sources": sources,
            "caveats": ["Answer generated from fallback reasoning (LLM unavailable)"],
            "confidence": 0.5,
        }
