"""Forecast Agent for AI Business Assistant."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ForecastAgentConfig(BaseModel):
    name: str = "forecast_agent"
    description: str = "Generates forecasts and predictions"
    model: str = "gpt-4"
    temperature: float = 0.2


class ForecastAgent:
    """Agent specialized for forecasting and predictions."""

    def __init__(self, config: ForecastAgentConfig | None = None) -> None:
        self.config = config or ForecastAgentConfig()
        self.name = self.config.name

    async def forecast(
        self,
        kpi: str,
        historical_data: list[float],
        horizon: int = 30,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        forecast_values = self._generate_forecast(historical_data, horizon)
        trend = self._determine_trend(historical_data)
        return {
            "agent": self.name,
            "kpi": kpi,
            "forecast_values": forecast_values,
            "trend": trend,
            "horizon": horizon,
            "confidence": self._calculate_confidence(historical_data, horizon),
        }

    def _generate_forecast(self, data: list[float], horizon: int) -> list[float]:
        if not data:
            return [0.0] * horizon
        avg = sum(data) / len(data)
        trend = (data[-1] - data[0]) / max(len(data), 1)
        forecast = []
        for i in range(horizon):
            val = avg + trend * (i + 1) / horizon
            forecast.append(round(val, 2))
        return forecast

    def _determine_trend(self, data: list[float]) -> str:
        if len(data) < 2:
            return "insufficient_data"
        if data[-1] > data[0]:
            return "upward"
        if data[-1] < data[0]:
            return "downward"
        return "stable"

    def _calculate_confidence(self, data: list[float], horizon: int) -> float:
        base = min(1.0, len(data) * 0.05)
        confidence = base * (1.0 - horizon * 0.01)
        return max(0.1, confidence)
