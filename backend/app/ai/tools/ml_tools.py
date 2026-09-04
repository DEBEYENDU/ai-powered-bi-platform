"""ML/Forecast tool implementations for AI Business Assistant."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.ai.tools.schemas import ForecastRequest, ForecastResponse


def run_forecast_tool(
    validated: BaseModel, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    if isinstance(validated, dict):
        validated = ForecastRequest(**validated)
    return ForecastResponse(
        kpi=validated.kpi,
        horizon=validated.horizon,
        forecast_values=[100000.0] * validated.horizon,
        model_type=validated.model_type,
        trained_at=datetime.utcnow(),
        accuracy=0.87,
    ).dict()


def predict_tool(validated: BaseModel, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"predictions": [0.85, 0.72, 0.91], "model": "classification", "confidence": 0.85}
