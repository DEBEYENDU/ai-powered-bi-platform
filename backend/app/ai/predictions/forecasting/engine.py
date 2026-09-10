"""Forecasting engine — Prophet, ARIMA, SARIMA, and statsmodels-based forecasting."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)


def _parse_horizon(horizon: str) -> int:
    """Parse horizon string like '30_days', '12_months', '52_weeks' into integer periods."""
    parts = horizon.lower().replace("_", " ").split()
    if len(parts) == 2:
        num = int(parts[0])
        unit = parts[1]
        if "month" in unit:
            return num * 30
        if "week" in unit:
            return num * 7
        if "year" in unit:
            return num * 365
        return num
    try:
        return int(parts[0])
    except (ValueError, IndexError):
        return 30


def forecast_prophet(
    df: pd.DataFrame,
    date_col: str,
    target_col: str,
    horizon: str = "30_days",
    confidence_level: float = 0.95,
    **kwargs: Any,
) -> dict[str, Any]:
    """Forecast using Facebook Prophet."""
    try:
        from prophet import Prophet
    except ImportError:
        return _fallback_forecast(df, date_col, target_col, horizon, "prophet")

    periods = _parse_horizon(horizon)
    freq = "D"

    prophet_df = df[[date_col, target_col]].copy()
    prophet_df.columns = ["ds", "y"]
    prophet_df["ds"] = pd.to_datetime(prophet_df["ds"], errors="coerce")
    prophet_df = prophet_df.dropna(subset=["ds", "y"])

    if len(prophet_df) < 10:
        return _fallback_forecast(df, date_col, target_col, horizon, "prophet")

    seasonality_mode = kwargs.get("seasonality_mode", "additive")
    m = Prophet(
        seasonality_mode=seasonality_mode,
        interval_width=confidence_level,
        daily_seasonality=False,
        weekly_seasonality=len(prophet_df) > 30,
        yearly_seasonality=len(prophet_df) > 365,
    )

    try:
        m.fit(prophet_df)
    except Exception:
        return _fallback_forecast(df, date_col, target_col, horizon, "prophet")

    future = m.make_future_dataframe(periods=periods, freq=freq)
    forecast = m.predict(future)

    # Extract predictions for future period only
    forecast_future = forecast.tail(periods)

    predictions: list[dict[str, Any]] = []
    for _, row in forecast_future.iterrows():
        predictions.append({
            "date": row["ds"].strftime("%Y-%m-%d"),
            "value": round(float(row["yhat"]), 4),
            "lower_bound": round(float(row["yhat_lower"]), 4),
            "upper_bound": round(float(row["yhat_upper"]), 4),
            "best_case": round(float(row["yhat_upper"]), 4),
            "worst_case": round(float(row["yhat_lower"]), 4),
        })

    # Compute trend
    if len(predictions) >= 2:
        first_val = predictions[0]["value"]
        last_val = predictions[-1]["value"]
        growth_pct = ((last_val - first_val) / max(abs(first_val), 1e-10)) * 100
        trend = "increasing" if growth_pct > 1 else "decreasing" if growth_pct < -1 else "stable"
    else:
        growth_pct = 0.0
        trend = "stable"

    return {
        "predictions": predictions,
        "trend": trend,
        "growth_percentage": round(growth_pct, 2),
        "model_type": "prophet",
        "confidence": confidence_level,
    }


def forecast_arima(
    df: pd.DataFrame,
    date_col: str,
    target_col: str,
    horizon: str = "30_days",
    confidence_level: float = 0.95,
    **kwargs: Any,
) -> dict[str, Any]:
    """Forecast using ARIMA (statsmodels)."""
    try:
        from statsmodels.tsa.arima.model import ARIMA
    except ImportError:
        return _fallback_forecast(df, date_col, target_col, horizon, "arima")

    periods = _parse_horizon(horizon)

    series = df[[date_col, target_col]].copy()
    series[date_col] = pd.to_datetime(series[date_col], errors="coerce")
    series = series.dropna().sort_values(date_col)
    series = series.set_index(date_col)[target_col]
    series = pd.to_numeric(series, errors="coerce").dropna()

    if len(series) < 10:
        return _fallback_forecast(df, date_col, target_col, horizon, "arima")

    order = kwargs.get("order", (1, 1, 1))

    try:
        model = ARIMA(series, order=order)
        fitted = model.fit()
        pred = fitted.get_forecast(steps=periods)
        pred_mean = pred.predicted_mean
        conf_int = pred.conf_int(alpha=1 - confidence_level)
    except Exception:
        try:
            model = ARIMA(series, order=(1, 0, 0))
            fitted = model.fit()
            pred = fitted.get_forecast(steps=periods)
            pred_mean = pred.predicted_mean
            conf_int = pred.conf_int(alpha=1 - confidence_level)
        except Exception:
            return _fallback_forecast(df, date_col, target_col, horizon, "arima")

    last_date = series.index[-1]
    dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=periods, freq="D")

    predictions: list[dict[str, Any]] = []
    for i, dt in enumerate(dates):
        val = float(pred_mean.iloc[i]) if i < len(pred_mean) else float(pred_mean.iloc[-1])
        lower = float(conf_int.iloc[i, 0]) if i < len(conf_int) else val * 0.9
        upper = float(conf_int.iloc[i, 1]) if i < len(conf_int) else val * 1.1
        predictions.append({
            "date": dt.strftime("%Y-%m-%d"),
            "value": round(val, 4),
            "lower_bound": round(lower, 4),
            "upper_bound": round(upper, 4),
            "best_case": round(upper, 4),
            "worst_case": round(lower, 4),
        })

    growth_pct = 0.0
    trend = "stable"
    if len(predictions) >= 2:
        growth_pct = ((predictions[-1]["value"] - predictions[0]["value"]) / max(abs(predictions[0]["value"]), 1e-10)) * 100
        trend = "increasing" if growth_pct > 1 else "decreasing" if growth_pct < -1 else "stable"

    return {
        "predictions": predictions,
        "trend": trend,
        "growth_percentage": round(growth_pct, 2),
        "model_type": "arima",
        "confidence": confidence_level,
    }


def forecast_sarima(
    df: pd.DataFrame,
    date_col: str,
    target_col: str,
    horizon: str = "30_days",
    confidence_level: float = 0.95,
    **kwargs: Any,
) -> dict[str, Any]:
    """Forecast using SARIMA (seasonal ARIMA)."""
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
    except ImportError:
        return forecast_arima(df, date_col, target_col, horizon, confidence_level, **kwargs)

    periods = _parse_horizon(horizon)

    series = df[[date_col, target_col]].copy()
    series[date_col] = pd.to_datetime(series[date_col], errors="coerce")
    series = series.dropna().sort_values(date_col)
    series = series.set_index(date_col)[target_col]
    series = pd.to_numeric(series, errors="coerce").dropna()

    if len(series) < 30:
        return forecast_arima(df, date_col, target_col, horizon, confidence_level, **kwargs)

    order = kwargs.get("order", (1, 1, 1))
    seasonal_order = kwargs.get("seasonal_order", (1, 1, 1, 12))

    try:
        model = SARIMAX(series, order=order, seasonal_order=seasonal_order)
        fitted = model.fit(disp=False, maxiter=200)
        pred = fitted.get_forecast(steps=periods)
        pred_mean = pred.predicted_mean
        conf_int = pred.conf_int(alpha=1 - confidence_level)
    except Exception:
        return forecast_arima(df, date_col, target_col, horizon, confidence_level, **kwargs)

    last_date = series.index[-1]
    dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=periods, freq="D")

    predictions: list[dict[str, Any]] = []
    for i, dt in enumerate(dates):
        val = float(pred_mean.iloc[i]) if i < len(pred_mean) else float(pred_mean.iloc[-1])
        lower = float(conf_int.iloc[i, 0]) if i < len(conf_int) else val * 0.9
        upper = float(conf_int.iloc[i, 1]) if i < len(conf_int) else val * 1.1
        predictions.append({
            "date": dt.strftime("%Y-%m-%d"),
            "value": round(val, 4),
            "lower_bound": round(lower, 4),
            "upper_bound": round(upper, 4),
            "best_case": round(upper, 4),
            "worst_case": round(lower, 4),
        })

    growth_pct = 0.0
    trend = "stable"
    if len(predictions) >= 2:
        growth_pct = ((predictions[-1]["value"] - predictions[0]["value"]) / max(abs(predictions[0]["value"]), 1e-10)) * 100
        trend = "increasing" if growth_pct > 1 else "decreasing" if growth_pct < -1 else "stable"

    return {
        "predictions": predictions,
        "trend": trend,
        "growth_percentage": round(growth_pct, 2),
        "model_type": "sarima",
        "confidence": confidence_level,
    }


def _fallback_forecast(
    df: pd.DataFrame,
    date_col: str,
    target_col: str,
    horizon: str,
    model_type: str,
) -> dict[str, Any]:
    """Simple linear extrapolation fallback when ML libraries are unavailable."""
    periods = _parse_horizon(horizon)

    series = pd.to_numeric(df[target_col], errors="coerce").dropna()
    if len(series) < 3:
        return {
            "predictions": [],
            "trend": "stable",
            "growth_percentage": 0.0,
            "model_type": model_type,
            "confidence": 0.5,
        }

    values = series.values.astype(float)
    x = np.arange(len(values), dtype=float)
    slope, intercept = np.polyfit(x, values, 1)

    mean_val = float(np.mean(values[-10:]))
    std_val = float(np.std(values[-10:])) if len(values) > 1 else mean_val * 0.1

    predictions: list[dict[str, Any]] = []
    for i in range(1, periods + 1):
        val = slope * (len(values) + i) + intercept
        margin = std_val * (1.96 if i <= 30 else 2.5)
        predictions.append({
            "date": f"day_{i}",
            "value": round(float(val), 4),
            "lower_bound": round(float(val - margin), 4),
            "upper_bound": round(float(val + margin), 4),
            "best_case": round(float(val + margin * 1.5), 4),
            "worst_case": round(float(val - margin * 1.5), 4),
        })

    growth_pct = 0.0
    trend = "stable"
    if len(predictions) >= 2:
        growth_pct = ((predictions[-1]["value"] - predictions[0]["value"]) / max(abs(predictions[0]["value"]), 1e-10)) * 100
        trend = "increasing" if growth_pct > 1 else "decreasing" if growth_pct < -1 else "stable"

    return {
        "predictions": predictions,
        "trend": trend,
        "growth_percentage": round(growth_pct, 2),
        "model_type": model_type,
        "confidence": 0.5,
    }
