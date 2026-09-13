"""Model monitoring — detect data drift, model drift, prediction drift,
and concept drift. Recommend retraining when drift is detected."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


def detect_data_drift(
    reference_data: pd.DataFrame,
    current_data: pd.DataFrame,
    threshold: float = 0.05,
) -> list[dict[str, Any]]:
    """Detect data drift using KS test and PSI for each numeric column."""
    drifts: list[dict[str, Any]] = []

    numeric_cols = reference_data.select_dtypes(include=[np.number]).columns
    common_cols = [c for c in numeric_cols if c in current_data.columns]

    for col in common_cols:
        ref = reference_data[col].dropna()
        cur = current_data[col].dropna()

        if len(ref) < 5 or len(cur) < 5:
            continue

        # KS test
        ks_stat, ks_p = stats.ks_2samp(ref, cur)

        # Population Stability Index
        psi = _compute_psi(ref.values, cur.values)

        # Mean shift
        mean_shift = abs(cur.mean() - ref.mean()) / max(abs(ref.mean()), 1e-10)

        # Variance ratio
        var_ratio = cur.var() / max(ref.var(), 1e-10)

        if ks_p < threshold or psi > 0.1:
            severity = "high" if psi > 0.25 or ks_p < 0.001 else "medium" if psi > 0.1 else "low"
            drifts.append(
                {
                    "drift_type": "data_drift",
                    "severity": severity,
                    "feature": col,
                    "description": (
                        f"{col}: KS p-value={ks_p:.4f}, PSI={psi:.4f}, mean shift={mean_shift:.2%}"
                    ),
                    "metrics": {
                        "ks_statistic": round(float(ks_stat), 4),
                        "ks_p_value": round(float(ks_p), 4),
                        "psi": round(float(psi), 4),
                        "mean_shift": round(float(mean_shift), 4),
                        "variance_ratio": round(float(var_ratio), 4),
                    },
                    "recommended_action": f"Investigate distribution changes in '{col}' and consider retraining",
                }
            )

    return drifts


def detect_prediction_drift(
    historical_predictions: list[float],
    recent_predictions: list[float],
    threshold: float = 0.1,
) -> list[dict[str, Any]]:
    """Detect drift in prediction distribution."""
    drifts: list[dict[str, Any]] = []

    if len(historical_predictions) < 10 or len(recent_predictions) < 5:
        return drifts

    ref = np.array(historical_predictions)
    cur = np.array(recent_predictions)

    # KS test
    ks_stat, ks_p = stats.ks_2samp(ref, cur)

    # Mean drift
    mean_drift = abs(cur.mean() - ref.mean()) / max(abs(ref.mean()), 1e-10)

    # Variance drift
    var_drift = abs(cur.var() - ref.var()) / max(ref.var(), 1e-10)

    if ks_p < 0.05 or mean_drift > threshold:
        severity = "high" if mean_drift > 0.3 else "medium" if mean_drift > 0.1 else "low"
        drifts.append(
            {
                "drift_type": "prediction_drift",
                "severity": severity,
                "feature": "predictions",
                "description": f"Prediction drift detected: mean shift={mean_drift:.2%}, KS p={ks_p:.4f}",
                "metrics": {
                    "ks_statistic": round(float(ks_stat), 4),
                    "ks_p_value": round(float(ks_p), 4),
                    "mean_drift": round(float(mean_drift), 4),
                    "variance_drift": round(float(var_drift), 4),
                },
                "recommended_action": "Retrain model with recent data to capture distribution shift",
            }
        )

    return drifts


def detect_concept_drift(
    y_true_recent: np.ndarray | list,
    y_pred_recent: np.ndarray | list,
    y_true_historical: np.ndarray | list,
    y_pred_historical: np.ndarray | list,
    threshold: float = 0.05,
) -> list[dict[str, Any]]:
    """Detect concept drift by comparing error distributions over time."""
    drifts: list[dict[str, Any]] = []

    err_recent = np.abs(np.array(y_true_recent, dtype=float) - np.array(y_pred_recent, dtype=float))
    err_historical = np.abs(
        np.array(y_true_historical, dtype=float) - np.array(y_pred_historical, dtype=float)
    )

    if len(err_recent) < 5 or len(err_historical) < 5:
        return drifts

    # Mann-Whitney U test
    _u_stat, u_p = stats.mannwhitneyu(err_historical, err_recent, alternative="two-sided")

    # Error ratio
    error_ratio = np.mean(err_recent) / max(np.mean(err_historical), 1e-10)

    if u_p < threshold or error_ratio > 1.5:
        severity = "high" if error_ratio > 2 else "medium" if error_ratio > 1.3 else "low"
        drifts.append(
            {
                "drift_type": "concept_drift",
                "severity": severity,
                "feature": "model_performance",
                "description": (
                    f"Concept drift detected: error ratio={error_ratio:.2f}x, U-test p={u_p:.4f}"
                ),
                "metrics": {
                    "error_ratio": round(float(error_ratio), 4),
                    "mann_whitney_p": round(float(u_p), 4),
                    "mean_error_recent": round(float(np.mean(err_recent)), 4),
                    "mean_error_historical": round(float(np.mean(err_historical)), 4),
                },
                "recommended_action": "Concept has shifted — retrain model with recent labeled data",
            }
        )

    return drifts


def _compute_psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """Compute Population Stability Index."""
    combined = np.concatenate([reference, current])
    breakpoints = np.percentile(combined, np.linspace(0, 100, bins + 1))
    breakpoints = np.unique(breakpoints)

    ref_counts = np.histogram(reference, bins=breakpoints)[0]
    cur_counts = np.histogram(current, bins=breakpoints)[0]

    # Add small constant to avoid division by zero
    ref_pct = (ref_counts + 1) / (len(reference) + bins)
    cur_pct = (cur_counts + 1) / (len(current) + bins)

    psi = float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))
    return max(0, psi)


def generate_monitoring_report(
    all_drifts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate a comprehensive monitoring report from all detected drifts."""
    n_drifts = len(all_drifts)
    high_drifts = [d for d in all_drifts if d["severity"] == "high"]
    medium_drifts = [d for d in all_drifts if d["severity"] == "medium"]

    if high_drifts:
        health = "critical"
        retrain = True
    elif medium_drifts:
        health = "warning"
        retrain = n_drifts > 3
    else:
        health = "healthy"
        retrain = False

    return {
        "overall_health": health,
        "total_drifts": n_drifts,
        "high_severity": len(high_drifts),
        "medium_severity": len(medium_drifts),
        "retraining_recommended": retrain,
        "drifts": all_drifts,
    }
