"""Natural Language Query Engine."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.ai.orchestrator.intent_detector import IntentDetector


class NLQEngine:
    """Parses natural language into structured analytics queries."""

    EXAMPLE_QUERIES = [
        "Show revenue by region.",
        "Why did sales decrease?",
        "Compare Q1 and Q2.",
        "What products generate highest profit?",
        "Forecast next month's revenue.",
        "Summarize today's dashboard.",
        "Show inventory anomalies.",
        "Which customers are likely to churn?",
    ]

    def __init__(self) -> None:
        self.detector = IntentDetector()

    def parse(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        detection = self.detector.detect(query, context)
        return {
            "original_query": query,
            "intent": detection.intent,
            "entities": detection.entities,
            "confidence": detection.confidence,
            "required_tools": detection.suggested_tools,
            "response_format": self._infer_format(query, detection.entities),
        }

    def _infer_format(self, query: str, entities: Dict[str, Any]) -> str:
        q = query.lower()
        if any(w in q for w in ["chart", "graph", "plot", "visualize"]):
            return "chart"
        if any(w in q for w in ["table", "list", "breakdown"]):
            return "table"
        if entities.get("comparison"):
            return "comparison"
        if entities.get("is_forecast"):
            return "forecast"
        return "text"

    def suggested_questions(self) -> List[str]:
        return list(self.EXAMPLE_QUERIES)
