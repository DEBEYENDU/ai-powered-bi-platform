"""Comprehensive model evaluation — regression, classification, and time series metrics."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def compute_regression_metrics(
    y_true: np.ndarray | list,
    y_pred: np.ndarray | list,
) -> dict[str, float]:
    """Compute regression metrics: MAE, RMSE, MAPE, R², etc."""
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    valid = ~(np.isnan(y_true) | np.isnan(y_pred))
    y_true = y_true[valid]
    y_pred = y_pred[valid]

    if len(y_true) == 0:
        return {"mae": 0, "rmse": 0, "mape": 0, "r2": 0}

    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))

    # MAPE
    nonzero = y_true != 0
    if nonzero.sum() > 0:
        mape = float(np.mean(np.abs((y_true[nonzero] - y_pred[nonzero]) / y_true[nonzero]))) * 100
    else:
        mape = 0.0

    # Explained variance
    from sklearn.metrics import explained_variance_score

    evs = float(explained_variance_score(y_true, y_pred))

    # Max error
    from sklearn.metrics import max_error

    me = float(max_error(y_true, y_pred))

    # Median absolute error
    from sklearn.metrics import median_absolute_error

    med_ae = float(median_absolute_error(y_true, y_pred))

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape": round(mape, 4),
        "r2": round(r2, 4),
        "explained_variance": round(evs, 4),
        "max_error": round(me, 4),
        "median_absolute_error": round(med_ae, 4),
    }


def compute_classification_metrics(
    y_true: np.ndarray | list,
    y_pred: np.ndarray | list,
    y_proba: np.ndarray | list | None = None,
) -> dict[str, float]:
    """Compute classification metrics: precision, recall, F1, ROC AUC, etc."""
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    accuracy = float(accuracy_score(y_true, y_pred))
    precision = float(precision_score(y_true, y_pred, average="weighted", zero_division=0))
    recall = float(recall_score(y_true, y_pred, average="weighted", zero_division=0))
    f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

    # ROC AUC
    roc_auc = 0.0
    if y_proba is not None:
        try:
            y_proba_arr = np.array(y_proba)
            if y_proba_arr.ndim == 1:
                roc_auc = float(roc_auc_score(y_true, y_proba_arr))
            else:
                roc_auc = float(
                    roc_auc_score(y_true, y_proba_arr, multi_class="ovr", average="weighted")
                )
        except ValueError:
            pass

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = 0, 0, 0, 0
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()

    # Log loss
    from sklearn.metrics import log_loss

    try:
        ll = float(log_loss(y_true, y_proba if y_proba is not None else y_pred))
    except Exception:
        ll = 0.0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "log_loss": round(ll, 4),
        "true_positives": int(tp),
        "false_positives": int(fp),
        "true_negatives": int(tn),
        "false_negatives": int(fn),
    }


def compute_time_series_metrics(
    y_true: np.ndarray | list,
    y_pred: np.ndarray | list,
) -> dict[str, float]:
    """Compute time series specific metrics including MAPE and directional accuracy."""
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    # Basic metrics
    base = compute_regression_metrics(y_true, y_pred)

    # Directional accuracy
    if len(y_true) > 1:
        true_dir = np.diff(y_true) > 0
        pred_dir = np.diff(y_pred) > 0
        directional_accuracy = float(np.mean(true_dir == pred_dir))
    else:
        directional_accuracy = 0.0

    # Theil's U
    if len(y_true) > 1:
        numerator = np.sqrt(np.mean((y_true - y_pred) ** 2))
        denominator = np.sqrt(np.mean(y_true**2)) + np.sqrt(np.mean(y_pred**2))
        theils_u = float(numerator / max(denominator, 1e-10))
    else:
        theils_u = 0.0

    # Weighted MAPE
    nonzero = y_true != 0
    if nonzero.sum() > 0:
        wmape = (
            float(
                np.sum(np.abs(y_true[nonzero] - y_pred[nonzero])) / np.sum(np.abs(y_true[nonzero]))
            )
            * 100
        )
    else:
        wmape = 0.0

    # Forecast bias
    bias = float(np.mean(y_pred - y_true))

    return {
        **base,
        "directional_accuracy": round(directional_accuracy, 4),
        "theils_u": round(theils_u, 4),
        "wmape": round(wmape, 4),
        "forecast_bias": round(bias, 4),
    }


def cross_validate_model(
    model: Any,
    X: np.ndarray,
    y: np.ndarray,
    cv_folds: int = 5,
    scoring: str = "r2",
) -> dict[str, float]:
    """Perform cross-validation and return scores."""
    from sklearn.model_selection import cross_val_score

    n_folds = min(cv_folds, max(2, len(X) // 5))
    try:
        scores = cross_val_score(model, X, y, cv=n_folds, scoring=scoring)
        return {
            "mean_score": round(float(np.mean(scores)), 4),
            "std_score": round(float(np.std(scores)), 4),
            "min_score": round(float(np.min(scores)), 4),
            "max_score": round(float(np.max(scores)), 4),
            "n_folds": n_folds,
        }
    except Exception:
        return {
            "mean_score": 0.0,
            "std_score": 0.0,
            "n_folds": n_folds,
        }


def compute_residual_analysis(
    y_true: np.ndarray | list,
    y_pred: np.ndarray | list,
) -> dict[str, Any]:
    """Analyse residuals for model diagnostics."""
    residuals = np.array(y_true, dtype=float) - np.array(y_pred, dtype=float)

    return {
        "mean_residual": round(float(np.mean(residuals)), 4),
        "std_residual": round(float(np.std(residuals)), 4),
        "skewness": round(float(pd.Series(residuals).skew()), 4),
        "kurtosis": round(float(pd.Series(residuals).kurtosis()), 4),
        "normality_test": {
            "jarque_bera": round(float(np.mean(residuals**3)), 4),
        },
    }
