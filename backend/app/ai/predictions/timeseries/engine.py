"""Time series engine — ARIMA, SARIMA, Prophet, LSTM for temporal predictions."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)


def detect_time_series(df: pd.DataFrame, date_col: str, target_col: str) -> dict[str, Any]:
    """Detect time series characteristics from the data."""
    series = df[[date_col, target_col]].copy()
    series[date_col] = pd.to_datetime(series[date_col], errors="coerce")
    series = series.dropna().sort_values(date_col)
    series[target_col] = pd.to_numeric(series[target_col], errors="coerce")
    series = series.dropna()

    if len(series) < 5:
        return {"is_time_series": False, "reason": "Insufficient data points"}

    n = len(series)
    values = series[target_col].values.astype(float)

    # Trend detection
    x = np.arange(n, dtype=float)
    slope = np.polyfit(x, values, 1)[0]
    mean_val = np.mean(values)
    trend_strength = abs(slope) / max(abs(mean_val), 1e-10)

    # Seasonality detection (autocorrelation at lag 7, 14, 30)
    autocorrs: dict[str, float] = {}
    for lag in [7, 14, 30]:
        if n > lag * 2:
            autocorr = float(np.corrcoef(values[:-lag], values[lag:])[0, 1])
            autocorrs[f"lag_{lag}"] = round(autocorr, 4)

    has_seasonality = any(abs(v) > 0.3 for v in autocorrs.values())

    # Volatility
    returns = np.diff(values) / np.where(values[:-1] == 0, 1, values[:-1])
    volatility = float(np.std(returns)) if len(returns) > 1 else 0.0

    # Frequency detection
    if n >= 2:
        dates = series[date_col].values
        diffs = np.diff(dates).astype("timedelta64[D]").astype(float)
        median_diff = float(np.median(diffs))
        if median_diff <= 1.5:
            freq = "daily"
        elif median_diff <= 8:
            freq = "weekly"
        elif median_diff <= 35:
            freq = "monthly"
        else:
            freq = "irregular"
    else:
        freq = "unknown"

    return {
        "is_time_series": True,
        "n_points": n,
        "frequency": freq,
        "has_trend": trend_strength > 0.01,
        "trend_direction": "increasing" if slope > 0 else "decreasing",
        "has_seasonality": has_seasonality,
        "seasonality_strength": autocorrs,
        "volatility": round(volatility, 4),
        "mean": round(float(mean_val), 4),
        "std": round(float(np.std(values)), 4),
        "min": round(float(np.min(values)), 4),
        "max": round(float(np.max(values)), 4),
        "date_range": {
            "start": series[date_col].iloc[0].strftime("%Y-%m-%d"),
            "end": series[date_col].iloc[-1].strftime("%Y-%m-%d"),
        },
    }


def prepare_lstm_data(
    series: np.ndarray,
    lookback: int = 30,
    train_ratio: float = 0.8,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Prepare data for LSTM training with sliding window."""
    if len(series) < lookback + 10:
        # Not enough data for LSTM
        lookback = max(2, len(series) // 4)

    X, y = [], []
    for i in range(lookback, len(series)):
        X.append(series[i - lookback : i])
        y.append(series[i])

    X_arr = np.array(X)
    y_arr = np.array(y)

    split = int(len(X_arr) * train_ratio)
    return X_arr[:split], y_arr[:split], X_arr[split:], y_arr[split:]


def train_lstm(
    series: np.ndarray,
    lookback: int = 30,
    epochs: int = 50,
    batch_size: int = 32,
) -> dict[str, Any]:
    """Train a simple LSTM model for time series forecasting."""
    try:
        import os
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
        import tensorflow as tf
        tf.get_logger().setLevel("ERROR")

        from tensorflow.keras.layers import LSTM, Dense, Dropout
        from tensorflow.keras.models import Sequential
    except ImportError:
        return {"error": "TensorFlow not installed", "fallback": True}

    X_train, y_train, X_test, y_test = prepare_lstm_data(series, lookback)

    if len(X_train) < 5:
        return {"error": "Insufficient data for LSTM"}

    # Normalize
    mean_val = np.mean(X_train)
    std_val = np.std(X_train) if np.std(X_train) > 0 else 1
    X_train_norm = (X_train - mean_val) / std_val
    X_test_norm = (X_test - mean_val) / std_val
    y_train_norm = (y_train - mean_val) / std_val

    # Reshape for LSTM [samples, timesteps, features]
    X_train_r = X_train_norm.reshape((X_train_norm.shape[0], X_train_norm.shape[1], 1))
    X_test_r = X_test_norm.reshape((X_test_norm.shape[0], X_test_norm.shape[1], 1))

    model = Sequential([
        LSTM(50, activation="relu", input_shape=(lookback, 1)),
        Dropout(0.2),
        LSTM(30, activation="relu"),
        Dropout(0.2),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")

    model.fit(
        X_train_r, y_train_norm,
        epochs=epochs,
        batch_size=batch_size,
        validation_split=0.1,
        verbose=0,
    )

    # Evaluate
    y_pred_norm = model.predict(X_test_r, verbose=0).flatten()
    y_pred = y_pred_norm * std_val + mean_val

    from sklearn.metrics import mean_absolute_error, mean_squared_error
    mae = mean_absolute_error(y_test, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))

    return {
        "model_type": "lstm",
        "metrics": {
            "mae": round(float(mae), 4),
            "rmse": round(rmse, 4),
            "lookback": lookback,
            "epochs": epochs,
        },
        "model": model,
        "normalization": {"mean": float(mean_val), "std": float(std_val)},
    }


def forecast_lstm(
    model: Any,
    series: np.ndarray,
    horizon: int = 30,
    lookback: int = 30,
) -> list[dict[str, Any]]:
    """Generate forecasts using a trained LSTM model."""
    if isinstance(model, dict) and "error" in model:
        return []

    norm_info = model.get("normalization", {"mean": 0, "std": 1})
    mean_val = norm_info["mean"]
    std_val = norm_info["std"]

    current_window = list(series[-lookback:])
    predictions: list[dict[str, Any]] = []

    try:
        import tensorflow as tf
        tf.get_logger().setLevel("ERROR")

        keras_model = model.get("model")
        if keras_model is None:
            return []

        for _ in range(horizon):
            window = np.array(current_window[-lookback:])
            window_norm = (window - mean_val) / std_val
            window_norm = window_norm.reshape(1, lookback, 1)

            pred_norm = keras_model.predict(window_norm, verbose=0).flatten()[0]
            pred = pred_norm * std_val + mean_val

            predictions.append({
                "value": round(float(pred), 4),
                "lower_bound": round(float(pred * 0.9), 4),
                "upper_bound": round(float(pred * 1.1), 4),
            })
            current_window.append(pred)
    except Exception:
        return []

    return predictions
