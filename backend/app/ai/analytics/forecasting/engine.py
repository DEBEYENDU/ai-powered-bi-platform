"""Forecasting algorithms: exponential smoothing, linear trend, seasonal decomposition."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from app.ai.analytics.statistics.engine import (
    _to_numeric_array,
    detect_seasonality,
    detect_trend,
)


def _exponential_smoothing_forecast(
    values: np.ndarray,
    horizon: int,
    alpha: float = 0.3,
) -> list[float]:
    """Simple exponential smoothing forecast."""
    n = len(values)
    if n == 0:
        return []

    # Initialise level with first observation
    level = float(values[0])
    for i in range(1, n):
        level = alpha * float(values[i]) + (1 - alpha) * level

    return [round(level, 4)] * horizon


def _double_exponential_smoothing_forecast(
    values: np.ndarray,
    horizon: int,
    alpha: float = 0.3,
    beta: float = 0.1,
) -> list[float]:
    """Holt's linear trend method (double exponential smoothing)."""
    n = len(values)
    if n < 2:
        return [round(float(values[0]), 4)] * horizon if n == 1 else []

    level = float(values[0])
    trend = float(values[1]) - float(values[0])

    for i in range(1, n):
        val = float(values[i])
        new_level = alpha * val + (1 - alpha) * (level + trend)
        trend = beta * (new_level - level) + (1 - beta) * trend
        level = new_level

    return [round(level + (i + 1) * trend, 4) for i in range(horizon)]


def _triple_exponential_smoothing_forecast(
    values: np.ndarray,
    horizon: int,
    period: int = 12,
    alpha: float = 0.3,
    beta: float = 0.1,
    gamma: float = 0.1,
) -> list[float]:
    """Holt-Winters method (triple exponential smoothing) for seasonal data."""
    n = len(values)
    if n < period * 2:
        return _double_exponential_smoothing_forecast(values, horizon, alpha, beta)

    # Initialise seasonal factors
    seasonal = np.zeros(n)
    for i in range(period):
        seasonal[i] = float(values[i]) / max(float(np.mean(values[:period])), 1e-10)

    level = float(np.mean(values[:period]))
    trend = (float(np.mean(values[period : 2 * period])) - float(np.mean(values[:period]))) / period

    # Update loop
    for i in range(period, n):
        val = float(values[i])
        prev_seasonal = seasonal[i - period] if i >= period else 1.0
        new_level = alpha * (val / max(prev_seasonal, 1e-10)) + (1 - alpha) * (level + trend)
        trend = beta * (new_level - level) + (1 - beta) * trend
        seasonal[i] = gamma * (val / max(new_level, 1e-10)) + (1 - gamma) * prev_seasonal
        level = new_level

    # Forecast
    result: list[float] = []
    for i in range(horizon):
        s_idx = n - period + (i % period)
        s_val = seasonal[s_idx] if s_idx < len(seasonal) else 1.0
        forecast_val = (level + (i + 1) * trend) * s_val
        result.append(round(float(forecast_val), 4))

    return result


def _linear_trend_forecast(values: np.ndarray, horizon: int) -> list[float]:
    """Forecast using linear regression on time index."""
    n = len(values)
    if n < 2:
        return [round(float(values[0]), 4)] * horizon if n == 1 else []

    x = np.arange(n, dtype=np.float64)
    slope, intercept = np.polyfit(x, values, 1)

    return [round(float(slope * (n + i) + intercept), 4) for i in range(horizon)]


def _compute_prediction_intervals(
    values: np.ndarray,
    forecasts: list[float],
    confidence: float = 0.95,
) -> list[tuple[float, float]]:
    """Compute prediction intervals using residual standard error."""
    n = len(values)
    if n < 3:
        return [(f, f) for f in forecasts]

    # Fit linear model to get residuals
    x = np.arange(n, dtype=np.float64)
    slope, intercept = np.polyfit(x, values, 1)
    predicted = slope * x + intercept
    residuals = values - predicted
    se = float(np.std(residuals, ddof=2))

    # Z-score for confidence level (approximate)
    z = 1.96 if confidence >= 0.95 else 1.645 if confidence >= 0.90 else 1.0

    intervals: list[tuple[float, float]] = []
    for i, f in enumerate(forecasts):
        # Increasing uncertainty with horizon
        horizon_se = se * math.sqrt(1 + (i + 1) / n)
        margin = z * horizon_se
        intervals.append((round(f - margin, 4), round(f + margin, 4)))

    return intervals


def generate_forecast(
    values: list[Any],
    horizon: int = 30,
    metric_name: str = "value",
    period: int | None = None,
) -> dict[str, Any]:
    """Generate a forecast for a numeric time series.

    Automatically selects the best method based on data characteristics.
    """
    arr = _to_numeric_array(values)
    n = len(arr)
    if n < 3:
        return {
            "metric": metric_name,
            "horizon_days": horizon,
            "points": [],
            "trend": "insufficient_data",
            "seasonality_detected": False,
            "confidence": "low",
        }

    # Detect trend and seasonality
    trend_info = detect_trend(values)
    season_info = detect_seasonality(values, period=period or 12)
    has_seasonality = season_info.get("seasonal", False)
    trend_dir = trend_info.get("direction", "flat")

    # Choose method
    if has_seasonality and n >= 24:
        forecasts = _triple_exponential_smoothing_forecast(arr, horizon, period=period or 12)
        method = "holt_winters"
    elif trend_dir != "flat":
        forecasts = _double_exponential_smoothing_forecast(arr, horizon)
        method = "holt_linear"
    else:
        forecasts = _exponential_smoothing_forecast(arr, horizon)
        method = "simple_exponential_smoothing"

    # Prediction intervals
    intervals = _compute_prediction_intervals(arr, forecasts)

    # Build points (using index-based dates — caller should map to real dates)
    points: list[dict[str, Any]] = []
    for i, (f, (lower, upper)) in enumerate(zip(forecasts, intervals, strict=False)):
        points.append({
            "index": n + i,
            "value": f,
            "lower_bound": lower,
            "upper_bound": upper,
        })

    # Confidence assessment
    r2 = trend_info.get("r_squared", 0)
    if r2 > 0.7 and n > 20:
        conf = "high"
    elif r2 > 0.3 or n > 10:
        conf = "medium"
    else:
        conf = "low"

    return {
        "metric": metric_name,
        "horizon_days": horizon,
        "method": method,
        "points": points,
        "trend": trend_dir,
        "trend_slope": trend_info.get("slope", 0),
        "seasonality_detected": has_seasonality,
        "seasonality_period": season_info.get("period"),
        "confidence": conf,
        "accuracy_score": round(r2, 4),
    }
