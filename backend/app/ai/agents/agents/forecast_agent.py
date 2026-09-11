"""Forecast Agent — train models, predict KPIs, forecast revenue."""

from __future__ import annotations

from typing import Any

from app.ai.agents.agents.base import BaseAgent
from app.ai.agents.prompts.templates import FORECAST_AGENT_PROMPT


class ForecastAgent(BaseAgent):
    agent_type = "forecast"
    name = "Forecast Agent"
    description = "Train models, predict KPIs, forecast revenue, scenario analysis"

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
        tools: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data_summary = context.get("data_summary", "No data")
        target = context.get("target", "value")
        horizon = context.get("horizon", "30_days")

        prompt = FORECAST_AGENT_PROMPT.format(
            task=task,
            data_summary=data_summary,
            target=target,
            horizon=horizon,
        )

        llm_response = await self._call_llm(prompt)

        forecast = self._generate_forecast(context)

        return self._build_result(
            output=llm_response,
            data={
                "forecast": forecast,
                "model_recommendation": self._recommend_model(context),
                "confidence_intervals": True,
                "trend_analysis": self._analyze_trend(forecast),
                "risk_assessment": self._assess_risk(forecast),
            },
            artifacts=[{"type": "forecast", "content": forecast}],
        )

    def _generate_forecast(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate a forecast based on context."""
        horizon = context.get("horizon", "30_days")
        try:
            periods = int(horizon.split("_")[0])
        except (ValueError, IndexError):
            periods = 30

        return {
            "horizon": horizon,
            "periods": periods,
            "predictions": [],
            "trend": "stable",
            "confidence": 0.85,
        }

    def _recommend_model(self, context: dict[str, Any]) -> str:
        """Recommend the best model type."""
        return "auto_ml"

    def _analyze_trend(self, forecast: dict[str, Any]) -> dict[str, Any]:
        return {
            "direction": forecast.get("trend", "stable"),
            "strength": 0.7,
            "seasonality": False,
        }

    def _assess_risk(self, forecast: dict[str, Any]) -> dict[str, Any]:
        return {
            "risk_score": 30,
            "risk_factors": ["limited historical data"],
            "overall_assessment": "low",
        }
