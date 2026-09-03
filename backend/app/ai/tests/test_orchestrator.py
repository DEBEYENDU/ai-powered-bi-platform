"""Tests for AI Orchestrator."""

import pytest
from app.ai.orchestrator.orchestrator import Orchestrator
from app.ai.orchestrator.intent_detector import IntentDetector, IntentDetection, IntentType


class TestIntentDetector:
    def test_detect_kpi_query(self):
        detector = IntentDetector()
        result = detector.detect("What is the revenue KPI?")
        assert result is not None
        assert result.confidence > 0

    def test_detect_revenue_analysis(self):
        detector = IntentDetector()
        result = detector.detect("Show me revenue by region")
        assert result.intent == IntentType.REVENUE_ANALYSIS

    def test_detect_forecast(self):
        detector = IntentDetector()
        result = detector.detect("Forecast next quarter revenue")
        assert result.intent == IntentType.FORECAST

    def test_detect_root_cause(self):
        detector = IntentDetector()
        result = detector.detect("Why did sales decrease?")
        assert result.intent == IntentType.ROOT_CAUSE

    def test_confidence_scores(self):
        detector = IntentDetector()
        result = detector.detect("Show revenue")
        assert 0.0 <= result.confidence <= 1.0

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.7

    @property
    def needs_human_review(self) -> bool:
        return self.confidence < 0.3


class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_process_query(self):
        orchestrator = Orchestrator()
        result = await orchestrator.process_query("What is revenue?")
        assert "response" in result
        assert "intent" in result

    @pytest.mark.asyncio
    async def test_process_query_with_context(self):
        orchestrator = Orchestrator()
        result = await orchestrator.process_query(
            "Show KPIs",
            user_id="user123",
            organization_id="org456",
        )
        assert result is not None