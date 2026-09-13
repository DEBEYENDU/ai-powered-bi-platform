from __future__ import annotations

import json

from app.ai.providers.base import ChatMessage
from app.ai.providers.registry import get_provider
from app.copilot.schemas.plan import IntentResult
from app.core.config import get_settings

INTENT_SYSTEM_PROMPT = """You are an intent classifier for a Business Intelligence platform.
Given a user request, classify the intent and extract key entities.

Possible intents:
- data_query: User wants to query/retrieve business data (SQL-compatible)
- data_analysis: User wants analysis of business data (trends, comparisons, insights)
- dashboard_creation: User wants to create or modify a dashboard
- report_generation: User wants to generate a business report
- forecasting: User wants predictions or forecasts
- knowledge_search: User wants to search company knowledge/policies/documents
- comparison: User wants to compare data across periods, regions, categories
- anomaly_analysis: User wants to understand unusual patterns
- data_quality: User wants to check data quality or clean data
- workflow_creation: User wants to create an automated workflow
- mixed_business_question: Request requires multiple capabilities
- clarification_required: Not enough information to proceed

Respond with ONLY a JSON object (no markdown, no extra text):
{
    "intent": "intent_name",
    "confidence": 0.0 to 1.0,
    "entities": {"metric": "...", "period": "...", "region": "...", "dataset_hint": "..."},
    "requires_clarification": false,
    "clarification_question": null
}

Entities may include: metric, period, region, dataset_hint, comparison_period, forecast_horizon, report_type, dashboard_prompt.
Only include entities that are clearly indicated or strongly implied by the request.
"""


class IntentService:
    def __init__(self):
        self.settings = get_settings()

    async def detect_intent(self, query: str, context: dict | None = None) -> IntentResult:
        """Classify user intent using the LLM."""
        provider = get_provider()
        model = self.settings.ai_model

        messages = [
            ChatMessage(role="system", content=INTENT_SYSTEM_PROMPT),
            ChatMessage(role="user", content=f"Classify this request: {query}"),
        ]

        try:
            response = await provider.chat(messages, model=model, temperature=0.1, max_tokens=500)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            result = json.loads(content)
            return IntentResult(
                intent=result.get("intent", "data_query"),
                confidence=min(1.0, max(0.0, result.get("confidence", 0.5))),
                entities=result.get("entities", {}),
                requires_clarification=result.get("requires_clarification", False),
                clarification_question=result.get("clarification_question"),
            )
        except Exception:
            return self._fallback_classify(query)

    def _fallback_classify(self, query: str) -> IntentResult:
        """Simple rule-based fallback when LLM is unavailable."""
        q = query.lower()

        if any(w in q for w in ["dashboard", "visualize", "chart", "widget"]):
            return IntentResult(intent="dashboard_creation", confidence=0.7, entities={})
        if any(w in q for w in ["report", "executive summary", "pdf"]):
            return IntentResult(intent="report_generation", confidence=0.7, entities={})
        if any(w in q for w in ["forecast", "predict", "future", "next quarter"]):
            return IntentResult(intent="forecasting", confidence=0.7, entities={})
        if any(w in q for w in ["policy", "document", "knowledge", "handbook", "procedure"]):
            return IntentResult(intent="knowledge_search", confidence=0.7, entities={})
        if any(w in q for w in ["compare", "vs", "versus", "against"]):
            return IntentResult(intent="comparison", confidence=0.7, entities={})
        if any(w in q for w in ["anomal", "unusual", "spike", "drop", "outlier"]):
            return IntentResult(intent="anomaly_analysis", confidence=0.7, entities={})
        if any(w in q for w in ["quality", "clean", "missing", "duplicate"]):
            return IntentResult(intent="data_quality", confidence=0.7, entities={})
        if any(w in q for w in ["workflow", "automate", "schedule", "notify", "alert me"]):
            return IntentResult(intent="workflow_creation", confidence=0.7, entities={})
        if any(w in q for w in ["analyze", "analysis", "insight", "trend", "why"]):
            return IntentResult(intent="data_analysis", confidence=0.6, entities={})

        return IntentResult(intent="data_query", confidence=0.5, entities={})
