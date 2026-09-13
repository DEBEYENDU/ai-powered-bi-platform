"""Anomaly detection algorithms: Z-score, IQR, rolling statistics, MAD."""

from __future__ import annotations

from typing import Any

import numpy as np

from app.ai.analytics.statistics.engine import _to_numeric_array


def detect_zscore_anomalies(
    values: list[Any],
    threshold: float = 3.0,
    metric_name: str = "value",
) -> list[dict[str, Any]]:
    """Detect anomalies using Z-score method.

    Points with |z| > threshold are flagged.
    """
    arr = _to_numeric_array(values)
    if len(arr) < 3:
        return []

    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr, ddof=1))
    if std_val == 0:
        return []

    anomalies: list[dict[str, Any]] = []
    for i, val in enumerate(arr):
        z = (float(val) - mean_val) / std_val
        if abs(z) > threshold:
            anomalies.append(
                {
                    "index": i,
                    "value": float(val),
                    "expected": round(mean_val, 2),
                    "z_score": round(float(z), 4),
                    "deviation_pct": round(((float(val) - mean_val) / abs(mean_val)) * 100, 2)
                    if mean_val != 0
                    else 0,
                    "severity": "high" if abs(z) > 4 else "medium" if abs(z) > 3 else "low",
                    "metric": metric_name,
                }
            )

    return anomalies


def detect_iqr_anomalies(
    values: list[Any],
    multiplier: float = 1.5,
    metric_name: str = "value",
) -> list[dict[str, Any]]:
    """Detect anomalies using the Interquartile Range (IQR) method."""
    arr = _to_numeric_array(values)
    if len(arr) < 4:
        return []

    q1 = float(np.percentile(arr, 25))
    q3 = float(np.percentile(arr, 75))
    iqr = q3 - q1
    if iqr == 0:
        return []

    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr

    anomalies: list[dict[str, Any]] = []
    for i, val in enumerate(arr):
        fv = float(val)
        if fv < lower_bound or fv > upper_bound:
            direction = "below" if fv < lower_bound else "above"
            anomalies.append(
                {
                    "index": i,
                    "value": fv,
                    "lower_bound": round(lower_bound, 2),
                    "upper_bound": round(upper_bound, 2),
                    "deviation_pct": round(((fv - (q1 + q3) / 2) / abs((q1 + q3) / 2)) * 100, 2)
                    if (q1 + q3) != 0
                    else 0,
                    "severity": "high" if abs(fv - (q1 + q3) / 2) > 2 * iqr else "medium",
                    "metric": metric_name,
                    "direction": direction,
                }
            )

    return anomalies


def detect_rolling_anomalies(
    values: list[Any],
    window: int = 7,
    threshold: float = 2.0,
    metric_name: str = "value",
) -> list[dict[str, Any]]:
    """Detect anomalies using rolling mean and standard deviation."""
    arr = _to_numeric_array(values)
    n = len(arr)
    if n < window + 1:
        return []

    anomalies: list[dict[str, Any]] = []
    for i in range(window, n):
        window_data = arr[i - window : i]
        rolling_mean = float(np.mean(window_data))
        rolling_std = float(np.std(window_data, ddof=1))
        if rolling_std == 0:
            continue

        z = (float(arr[i]) - rolling_mean) / rolling_std
        if abs(z) > threshold:
            anomalies.append(
                {
                    "index": i,
                    "value": float(arr[i]),
                    "rolling_mean": round(rolling_mean, 2),
                    "rolling_std": round(rolling_std, 2),
                    "z_score": round(float(z), 4),
                    "severity": "high" if abs(z) > 3 else "medium",
                    "metric": metric_name,
                    "window": window,
                }
            )

    return anomalies


def detect_mad_anomalies(
    values: list[Any],
    threshold: float = 3.5,
    metric_name: str = "value",
) -> list[dict[str, Any]]:
    """Detect anomalies using Median Absolute Deviation (MAD).

    More robust to outliers than Z-score.
    """
    arr = _to_numeric_array(values)
    if len(arr) < 3:
        return []

    median_val = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median_val)))
    if mad == 0:
        return []

    # Modified Z-score
    anomalies: list[dict[str, Any]] = []
    for i, val in enumerate(arr):
        modified_z = 0.6745 * (float(val) - median_val) / mad
        if abs(modified_z) > threshold:
            anomalies.append(
                {
                    "index": i,
                    "value": float(val),
                    "median": round(median_val, 2),
                    "mad": round(mad, 2),
                    "modified_z_score": round(float(modified_z), 4),
                    "severity": "high" if abs(modified_z) > 5 else "medium",
                    "metric": metric_name,
                }
            )

    return anomalies


def detect_missing_values(data: list[dict[str, Any]], columns: list[str]) -> list[dict[str, Any]]:
    """Detect missing values in specified columns."""
    anomalies: list[dict[str, Any]] = []
    total = len(data)

    for col in columns:
        missing_count = sum(1 for row in data if row.get(col) is None or row.get(col) == "")
        if missing_count > 0:
            pct = (missing_count / total) * 100 if total > 0 else 0
            anomalies.append(
                {
                    "type": "missing_values",
                    "metric": col,
                    "missing_count": missing_count,
                    "total_rows": total,
                    "missing_pct": round(pct, 2),
                    "severity": "high" if pct > 10 else "medium" if pct > 5 else "low",
                }
            )

    return anomalies


def detect_duplicates(data: list[dict[str, Any]], key_columns: list[str]) -> list[dict[str, Any]]:
    """Detect duplicate records based on key columns."""
    seen: dict[str, int] = {}
    for row in data:
        key = tuple(str(row.get(c, "")) for c in key_columns)
        key_str = "|".join(key)
        seen[key_str] = seen.get(key_str, 0) + 1

    duplicates = {k: v for k, v in seen.items() if v > 1}
    if not duplicates:
        return []

    total_dupes = sum(v - 1 for v in duplicates.values())
    return [
        {
            "type": "duplicate_records",
            "duplicate_groups": len(duplicates),
            "duplicate_rows": total_dupes,
            "key_columns": key_columns,
            "severity": "medium" if total_dupes < len(data) * 0.05 else "high",
        }
    ]


def detect_all_anomalies(
    data: list[dict[str, Any]],
    numeric_columns: list[str],
    date_column: str | None = None,
) -> list[dict[str, Any]]:
    """Run all anomaly detection methods on the dataset and merge results."""
    all_anomalies: list[dict[str, Any]] = []

    for col in numeric_columns:
        values = [row.get(col) for row in data]

        # Z-score
        all_anomalies.extend(detect_zscore_anomalies(values, metric_name=col))

        # IQR
        all_anomalies.extend(detect_iqr_anomalies(values, metric_name=col))

        # MAD
        all_anomalies.extend(detect_mad_anomalies(values, metric_name=col))

    # Rolling anomalies (if date column exists and data is time-ordered)
    if date_column and numeric_columns:
        first_metric = numeric_columns[0]
        values = [row.get(first_metric) for row in data]
        all_anomalies.extend(detect_rolling_anomalies(values, metric_name=first_metric))

    # Missing values
    all_anomalies.extend(detect_missing_values(data, numeric_columns))

    # Duplicates
    if numeric_columns:
        all_anomalies.extend(detect_duplicates(data, numeric_columns[:2]))

    return all_anomalies
