"""Intent detection engine for natural language queries."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


class IntentType:
    KPI_QUERY = "kpi_query"
    REVENUE_ANALYSIS = "revenue_analysis"
    SALES_ANALYSIS = "sales_analysis"
    FORECAST = "forecast"
    PREDICTION = "prediction"
    DASHBOARD_SUMMARY = "dashboard_summary"
    ROOT_CAUSE = "root_cause"
    RECOMMENDATION = "recommendation"
    EXECUTIVE_SUMMARY = "executive_summary"
    REPORT_GENERATION = "report_generation"
    DATASET_SEARCH = "dataset_search"
    CHART_REQUEST = "chart_request"
    INSIGHT_REQUEST = "insight_request"
    GENERAL_CHAT = "general_chat"
    ANOMALY_DETECTION = "anomaly_detection"
    TREND_ANALYSIS = "trend_analysis"
    COMPARISON = "comparison"


class IntentMapping:
    INTENT_PATTERNS = {
        IntentType.KPI_QUERY: ["kpi", "metric", "performance", "measure", "calculate"],
        IntentType.REVENUE_ANALYSIS: [
            "revenue",
            "income",
            "sales revenue",
            "total revenue",
            "revenue by",
            "revenue trend",
        ],
        IntentType.SALES_ANALYSIS: ["sales", "sales performance", "sales trend", "sales by"],
        IntentType.FORECAST: [
            "forecast",
            "predict",
            "predictive",
            "future",
            "what will",
            "next month",
            "next quarter",
            "next year",
            "outlook",
        ],
        IntentType.PREDICTION: [
            "predict",
            "prediction",
            "likely",
            "churn",
            "will happen",
            "probability",
            "risk",
            "likelihood",
        ],
        IntentType.DASHBOARD_SUMMARY: [
            "dashboard",
            "summary",
            "summarize",
            "overview",
            "show dashboard",
            "executive summary",
        ],
        IntentType.ROOT_CAUSE: [
            "why did",
            "why is",
            "why has",
            "reason for",
            "root cause",
            "cause of",
            "why are",
            "why was",
        ],
        IntentType.RECOMMENDATION: [
            "recommend",
            "suggest",
            "what should",
            "what can we",
            "how can we",
            "advice",
            "what to do",
        ],
        IntentType.EXECUTIVE_SUMMARY: [
            "executive summary",
            "board report",
            "ceo briefing",
            "quarterly summary",
            "annual summary",
            "weekly summary",
            "monthly summary",
        ],
        IntentType.REPORT_GENERATION: [
            "report",
            "generate report",
            "create report",
            "sales report",
            "financial report",
        ],
        IntentType.DATASET_SEARCH: [
            "dataset",
            "data source",
            "find data",
            "available data",
            "datasets",
        ],
        IntentType.CHART_REQUEST: ["chart", "graph", "visualize", "show chart", "plot"],
        IntentType.ANOMALY_DETECTION: ["anomaly", "anomalies", "unusual", "outlier", "abnormal"],
        IntentType.TREND_ANALYSIS: ["trend", "trending", "seasonality", "cyclical"],
        IntentType.COMPARISON: ["compare", "comparison", "versus", "vs", "vs.", "compared to"],
    }
    KPI_KEYWORDS = [
        "revenue",
        "profit",
        "margin",
        "roi",
        "roas",
        "growth",
        "churn",
        "retention",
        "conversion",
        "ltv",
        "aov",
        "inventory",
        "cost",
    ]
    TIME_KEYWORDS = [
        "today",
        "yesterday",
        "this week",
        "last week",
        "this month",
        "last month",
        "this quarter",
        "last quarter",
        "this year",
        "last year",
    ]
    DIMENSION_KEYWORDS = [
        "region",
        "product",
        "category",
        "customer",
        "segment",
        "channel",
        "department",
        "country",
        "state",
    ]


class IntentDetector:
    def __init__(self) -> None:
        self._compiled_patterns = {
            intent: [re.compile(pat, re.IGNORECASE) for pat in patterns]
            for intent, patterns in IntentMapping.INTENT_PATTERNS.items()
        }

    def detect(self, query: str, context: dict[str, Any] | None = None) -> IntentDetection:
        query_lower = query.lower().strip()
        intent_scores: dict[str, float] = {}
        for intent, patterns in self._compiled_patterns.items():
            score = 0.0
            for pattern in patterns:
                if pattern.search(query_lower):
                    # Specificity weighting: longer (more specific) phrases
                    # outrank generic single keywords. This breaks ties like
                    # "Why did sales decrease?" where "why did" (question
                    # intent) must beat the generic "sales" keyword.
                    score += len(pattern.pattern)
            if score > 0:
                intent_scores[intent] = score
        if not intent_scores:
            primary_intent = IntentType.GENERAL_CHAT
            intent_scores[primary_intent] = 0.1
        else:
            primary_intent = max(intent_scores, key=intent_scores.get)
        confidence = self._calculate_confidence(intent_scores, primary_intent)
        entities = self._extract_entities(query_lower)
        secondary_intent = self._detect_secondary_intent(query_lower, primary_intent)
        suggested_tools = self._suggest_tools(primary_intent, secondary_intent, entities)
        return IntentDetection(
            intent=primary_intent,
            entities=entities,
            confidence=round(confidence, 4),
            suggested_tools=suggested_tools,
        )

    def _calculate_confidence(self, scores: dict[str, float], primary_intent: str) -> float:
        primary_score = scores.get(primary_intent, 0)
        total_score = sum(scores.values())
        if total_score == 0:
            return 0.1
        raw_confidence = primary_score / total_score
        if primary_score >= 3:
            raw_confidence = min(1.0, raw_confidence * 1.2)
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) >= 2 and sorted_scores[0] - sorted_scores[1] < 0.5:
            raw_confidence *= 0.8
        return min(1.0, max(0.1, raw_confidence))

    def _extract_entities(self, query_lower: str) -> dict[str, Any]:
        entities: dict[str, Any] = {
            "kpi_keywords": [],
            "time_range": None,
            "dimensions": [],
            "comparison": False,
            "is_forecast": False,
        }
        for kw in IntentMapping.KPI_KEYWORDS:
            if kw.lower() in query_lower:
                entities["kpi_keywords"].append(kw)
        for kw in IntentMapping.TIME_KEYWORDS:
            if kw.lower() in query_lower:
                entities["time_range"] = kw
                break
        for kw in IntentMapping.DIMENSION_KEYWORDS:
            if kw.lower() in query_lower:
                entities["dimensions"].append(kw)
        for comp_kw in ["compare", "comparison", "versus", "vs", "vs.", "compared to"]:
            if comp_kw in query_lower:
                entities["comparison"] = True
                break
        for fc_kw in ["forecast", "predict", "future", "next month", "next quarter", "next year"]:
            if fc_kw in query_lower:
                entities["is_forecast"] = True
                break
        return entities

    def _detect_secondary_intent(self, query_lower: str, primary_intent: str) -> str | None:
        secondary_candidates = []
        for intent, patterns in self._compiled_patterns.items():
            if intent == primary_intent:
                continue
            for pattern in patterns:
                if pattern.search(query_lower):
                    secondary_candidates.append((intent, pattern))
                    break
        if len(secondary_candidates) == 1:
            return secondary_candidates[0][0]
        elif len(secondary_candidates) > 1:
            return max(secondary_candidates, key=lambda x: len(x[1]))[0]
        return None

    def _suggest_tools(
        self, primary_intent: str, secondary_intent: str | None, entities: dict[str, Any]
    ) -> list[str]:
        tool_mapping = {
            IntentType.KPI_QUERY: ["calculate_kpi"],
            IntentType.REVENUE_ANALYSIS: ["revenue_analytics"],
            IntentType.SALES_ANALYSIS: ["sales_analytics"],
            IntentType.FORECAST: ["run_forecast"],
            IntentType.PREDICTION: ["predict"],
            IntentType.DASHBOARD_SUMMARY: ["get_dashboard_summary"],
            IntentType.ROOT_CAUSE: ["root_cause_analysis"],
            IntentType.RECOMMENDATION: ["generate_recommendations"],
            IntentType.EXECUTIVE_SUMMARY: ["generate_executive_summary"],
            IntentType.REPORT_GENERATION: ["generate_report"],
            IntentType.DATASET_SEARCH: ["search_datasets"],
            IntentType.CHART_REQUEST: ["generate_chart"],
            IntentType.ANOMALY_DETECTION: ["detect_anomalies"],
            IntentType.TREND_ANALYSIS: ["analyze_trends"],
            IntentType.COMPARISON: ["compare_metrics"],
        }
        tools = list(tool_mapping.get(primary_intent, []))
        if secondary_intent and secondary_intent in tool_mapping:
            tools.extend(tool_mapping[secondary_intent])
        if (
            entities.get("comparison") or entities.get("kpi_keywords")
        ) and "generate_chart" not in tools:
            tools.append("generate_chart")
        return tools


class IntentDetection(BaseModel):
    intent: str = Field(..., description="Primary detected intent")
    entities: dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    suggested_tools: list[str] = Field(default_factory=list, description="Suggested tool names")

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.7

    @property
    def needs_human_review(self) -> bool:
        return self.confidence < 0.3
