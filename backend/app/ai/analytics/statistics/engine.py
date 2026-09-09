"""Core statistical computations: trend detection, correlation, growth, seasonality."""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def _to_numeric_array(values: list[Any]) -> np.ndarray:
    """Convert a list of mixed values to a float numpy array, dropping non-numeric."""
    cleaned: list[float] = []
    for v in values:
        try:
            cleaned.append(float(v))
        except (TypeError, ValueError):
            continue
    return np.array(cleaned, dtype=np.float64)


def compute_basic_stats(values: list[Any]) -> dict[str, Any]:
    """Compute descriptive statistics for a numeric series."""
    arr = _to_numeric_array(values)
    if len(arr) == 0:
        return {"count": 0, "mean": 0, "std": 0, "min": 0, "max": 0, "median": 0}

    return {
        "count": len(arr),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "median": float(np.median(arr)),
        "sum": float(np.sum(arr)),
        "q25": float(np.percentile(arr, 25)),
        "q75": float(np.percentile(arr, 75)),
    }


def detect_trend(values: list[Any]) -> dict[str, Any]:
    """Detect linear trend in a numeric series using least-squares regression.

    Returns slope, direction, strength (R²), and percentage change.
    """
    arr = _to_numeric_array(values)
    n = len(arr)
    if n < 2:
        return {"direction": "flat", "slope": 0.0, "r_squared": 0.0, "change_pct": 0.0}

    x = np.arange(n, dtype=np.float64)
    slope, intercept = np.polyfit(x, arr, 1)

    # R² calculation
    y_pred = slope * x + intercept
    ss_res = np.sum((arr - y_pred) ** 2)
    ss_tot = np.sum((arr - np.mean(arr)) ** 2)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Percentage change
    first_val = float(arr[0]) if arr[0] != 0 else 1.0
    change_pct = ((float(arr[-1]) - float(arr[0])) / abs(first_val)) * 100

    if slope > 0.01:
        direction = "up"
    elif slope < -0.01:
        direction = "down"
    else:
        direction = "flat"

    return {
        "direction": direction,
        "slope": float(slope),
        "r_squared": float(r_squared),
        "change_pct": round(change_pct, 2),
        "first_value": float(arr[0]),
        "last_value": float(arr[-1]),
        "mean": float(np.mean(arr)),
    }


def compute_growth_rate(values: list[Any]) -> dict[str, Any]:
    """Compute period-over-period growth rates."""
    arr = _to_numeric_array(values)
    if len(arr) < 2:
        return {"growth_rates": [], "avg_growth": 0.0, "acceleration": 0.0}

    growth_rates: list[float] = []
    for i in range(1, len(arr)):
        prev = float(arr[i - 1])
        curr = float(arr[i])
        if prev != 0:
            growth_rates.append(((curr - prev) / abs(prev)) * 100)
        else:
            growth_rates.append(0.0)

    avg_growth = float(np.mean(growth_rates)) if growth_rates else 0.0

    # Acceleration: is growth speeding up or slowing down?
    acceleration = 0.0
    if len(growth_rates) >= 2:
        acceleration = float(growth_rates[-1] - growth_rates[0])

    return {
        "growth_rates": [round(g, 2) for g in growth_rates],
        "avg_growth": round(avg_growth, 2),
        "max_growth": round(max(growth_rates), 2) if growth_rates else 0.0,
        "min_growth": round(min(growth_rates), 2) if growth_rates else 0.0,
        "acceleration": round(acceleration, 2),
    }


def compute_correlation(x_values: list[Any], y_values: list[Any]) -> dict[str, Any]:
    """Compute Pearson correlation between two numeric series."""
    x_arr = _to_numeric_array(x_values)
    y_arr = _to_numeric_array(y_values)

    min_len = min(len(x_arr), len(y_arr))
    if min_len < 3:
        return {"correlation": 0.0, "strength": "none", "p_value": 1.0}

    x_arr = x_arr[:min_len]
    y_arr = y_arr[:min_len]

    corr = float(np.corrcoef(x_arr, y_arr)[0, 1])

    abs_corr = abs(corr)
    if abs_corr >= 0.7:
        strength = "strong"
    elif abs_corr >= 0.4:
        strength = "moderate"
    elif abs_corr >= 0.2:
        strength = "weak"
    else:
        strength = "none"

    # Simplified p-value approximation using t-distribution
    t_stat = corr * math.sqrt((min_len - 2) / (1 - corr ** 2)) if abs(corr) < 1.0 else float("inf")

    return {
        "correlation": round(corr, 4),
        "strength": strength,
        "t_statistic": round(t_stat, 4),
        "sample_size": min_len,
    }


def detect_seasonality(values: list[Any], period: int = 12) -> dict[str, Any]:
    """Detect seasonality using autocorrelation."""
    arr = _to_numeric_array(values)
    n = len(arr)
    if n < period * 2:
        return {"seasonal": False, "period": period, "strength": 0.0}

    # Demean
    mean_val = float(np.mean(arr))
    demeaned = arr - mean_val

    # Autocorrelation at the given lag
    var = float(np.var(demeaned))
    if var == 0:
        return {"seasonal": False, "period": period, "strength": 0.0}

    lag = period
    autocorr = float(np.sum(demeaned[lag:] * demeaned[:-lag]) / (n * var))

    return {
        "seasonal": abs(autocorr) > 0.3,
        "period": period,
        "autocorrelation": round(autocorr, 4),
        "strength": "strong" if abs(autocorr) > 0.6 else "moderate" if abs(autocorr) > 0.3 else "weak",
    }


def compute_volatility(values: list[Any]) -> dict[str, Any]:
    """Compute volatility metrics (coefficient of variation, max drawdown)."""
    arr = _to_numeric_array(values)
    if len(arr) < 2:
        return {"cv": 0.0, "max_drawdown": 0.0, "volatility": "low"}

    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr, ddof=1))
    cv = (std_val / abs(mean_val)) * 100 if mean_val != 0 else 0.0

    # Max drawdown
    peak = arr[0]
    max_dd = 0.0
    for val in arr:
        if val > peak:
            peak = val
        dd = (peak - val) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    if cv < 10:
        vol_label = "low"
    elif cv < 30:
        vol_label = "moderate"
    else:
        vol_label = "high"

    return {
        "cv": round(cv, 2),
        "max_drawdown": round(float(max_dd) * 100, 2),
        "volatility": vol_label,
        "coefficient_of_variation": round(cv, 2),
    }


def compare_periods(
    current: list[Any], previous: list[Any]
) -> dict[str, Any]:
    """Compare two periods and compute absolute and percentage changes."""
    curr_stats = compute_basic_stats(current)
    prev_stats = compute_basic_stats(previous)

    curr_sum = curr_stats.get("sum", 0)
    prev_sum = prev_stats.get("sum", 0)
    curr_mean = curr_stats.get("mean", 0)
    prev_mean = prev_stats.get("mean", 0)

    abs_change = curr_sum - prev_sum
    pct_change = ((curr_sum - prev_sum) / abs(prev_sum) * 100) if prev_sum != 0 else 0.0
    mean_change = curr_mean - prev_mean
    mean_pct = ((curr_mean - prev_mean) / abs(prev_mean) * 100) if prev_mean != 0 else 0.0

    return {
        "current_total": round(curr_sum, 2),
        "previous_total": round(prev_sum, 2),
        "absolute_change": round(abs_change, 2),
        "percentage_change": round(pct_change, 2),
        "current_mean": round(curr_mean, 2),
        "previous_mean": round(prev_mean, 2),
        "mean_change": round(mean_change, 2),
        "mean_percentage_change": round(mean_pct, 2),
    }


def rank_values(
    data: list[dict[str, Any]], key: str, top_n: int = 5
) -> dict[str, Any]:
    """Rank items by a numeric key and return top/bottom N."""
    valid = []
    for item in data:
        val = item.get(key)
        try:
            valid.append({"item": item, "value": float(val)})
        except (TypeError, ValueError):
            continue

    valid.sort(key=lambda x: x["value"], reverse=True)
    top = [v["item"] for v in valid[:top_n]]
    bottom = [v["item"] for v in valid[-top_n:]] if len(valid) > top_n else []

    return {
        "top": top,
        "bottom": list(reversed(bottom)),
        "total_items": len(valid),
        "max_value": valid[0]["value"] if valid else 0,
        "min_value": valid[-1]["value"] if valid else 0,
    }
