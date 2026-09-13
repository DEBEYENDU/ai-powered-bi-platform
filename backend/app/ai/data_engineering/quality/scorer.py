"""Multi-dimensional data quality scoring — computes per-dimension scores
(Completeness, Consistency, Accuracy, Uniqueness, Validity, Timeliness)
and an overall weighted composite."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.ai.data_engineering.schemas import QualityScore


def compute_quality_score(
    df: pd.DataFrame,
    issues: list[dict[str, Any]] | None = None,
) -> QualityScore:
    """Compute multi-dimensional quality score for a DataFrame."""
    n_rows = len(df)
    n_cols = len(df.columns)

    if n_rows == 0 or n_cols == 0:
        return QualityScore(
            overall=100,
            completeness=100,
            consistency=100,
            accuracy=100,
            uniqueness=100,
            validity=100,
            timeliness=100,
        )

    # ---- Completeness ----
    total_cells = n_rows * n_cols
    missing = int(df.isna().sum().sum())
    completeness = round(max(0, (1 - missing / total_cells) * 100), 1) if total_cells > 0 else 100.0

    # ---- Uniqueness ----
    dup_rows = int(df.duplicated().sum())
    uniqueness = round(max(0, (1 - dup_rows / n_rows) * 100), 1) if n_rows > 0 else 100.0

    # ---- Consistency ----
    consistency_scores: list[float] = []
    for col in df.columns:
        series = df[col].dropna()
        if len(series) == 0:
            consistency_scores.append(100.0)
            continue
        # Check type consistency
        types = series.map(type).nunique()
        type_score = max(0, 100 - (types - 1) * 25)
        # Check format consistency for text columns
        if series.dtype == object and len(series) > 5:
            lengths = series.astype(str).str.len()
            cv = lengths.std() / max(lengths.mean(), 1)
            format_score = max(0, 100 - cv * 30)
            consistency_scores.append((type_score + format_score) / 2)
        else:
            consistency_scores.append(type_score)
    consistency = round(float(np.mean(consistency_scores)), 1) if consistency_scores else 100.0

    # ---- Accuracy ----
    accuracy_parts: list[float] = []
    for col in df.columns:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        # Numeric ranges
        if pd.api.types.is_numeric_dtype(series):
            numeric = pd.to_numeric(series, errors="coerce").dropna()
            if len(numeric) > 10:
                q1, q3 = numeric.quantile([0.25, 0.75])
                iqr = q3 - q1
                outliers = int(((numeric < q1 - 3 * iqr) | (numeric > q3 + 3 * iqr)).sum())
                accuracy_parts.append(max(0, 100 - outliers / len(numeric) * 100))
            else:
                accuracy_parts.append(95.0)
        # Text columns — low null rate = high accuracy proxy
        elif series.dtype == object:
            null_rate = df[col].isna().sum() / max(n_rows, 1)
            accuracy_parts.append(max(0, 100 - null_rate * 50))
    accuracy = round(float(np.mean(accuracy_parts)), 1) if accuracy_parts else 95.0

    # ---- Validity ----
    validity_parts: list[float] = []
    for col in df.columns:
        series = df[col]
        null_pct = series.isna().sum() / max(n_rows, 1) * 100
        # Low nulls = high validity
        validity_parts.append(max(0, 100 - null_pct * 0.8))
    validity = round(float(np.mean(validity_parts)), 1) if validity_parts else 100.0

    # ---- Timeliness ----
    # Heuristic: check for date columns and their recency
    date_cols = []
    for col in df.columns:
        try:
            dates = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
            if dates.notna().sum() > len(df) * 0.5:
                date_cols.append(dates)
        except Exception:
            pass

    if date_cols:
        timeliness_parts: list[float] = []
        for dates in date_cols:
            valid_dates = dates.dropna()
            if len(valid_dates) > 0:
                max_date = valid_dates.max()
                days_old = (pd.Timestamp.now() - max_date).days
                if days_old <= 1:
                    timeliness_parts.append(100.0)
                elif days_old <= 7:
                    timeliness_parts.append(90.0)
                elif days_old <= 30:
                    timeliness_parts.append(80.0)
                elif days_old <= 90:
                    timeliness_parts.append(70.0)
                else:
                    timeliness_parts.append(max(40, 100 - days_old * 0.1))
            else:
                timeliness_parts.append(70.0)
        timeliness = round(float(np.mean(timeliness_parts)), 1)
    else:
        timeliness = 85.0  # No date columns — neutral score

    # ---- Overall (weighted) ----
    overall = round(
        completeness * 0.25
        + consistency * 0.20
        + accuracy * 0.20
        + uniqueness * 0.15
        + validity * 0.15
        + timeliness * 0.05,
        1,
    )

    # Deduct for known issues
    if issues:
        severity_deduction = {
            "critical": 10,
            "high": 6,
            "medium": 3,
            "low": 1,
        }
        total_deduction = sum(severity_deduction.get(i.get("severity", "low"), 2) for i in issues)
        overall = max(0, overall - min(total_deduction, 30))

    return QualityScore(
        overall=overall,
        completeness=completeness,
        consistency=consistency,
        accuracy=accuracy,
        uniqueness=uniqueness,
        validity=validity,
        timeliness=timeliness,
    )


def score_dimension_breakdown(df: pd.DataFrame) -> dict[str, Any]:
    """Return a detailed breakdown of each quality dimension."""
    n_rows = len(df)
    total_cells = n_rows * len(df.columns)

    missing_per_col = {col: int(df[col].isna().sum()) for col in df.columns}
    dup_rows = int(df.duplicated().sum())

    return {
        "total_rows": n_rows,
        "total_columns": len(df.columns),
        "total_cells": total_cells,
        "missing_cells": sum(missing_per_col.values()),
        "duplicate_rows": dup_rows,
        "missing_per_column": missing_per_col,
        "completeness_pct": round(
            (1 - sum(missing_per_col.values()) / max(total_cells, 1)) * 100, 2
        ),
        "uniqueness_pct": round((1 - dup_rows / max(n_rows, 1)) * 100, 2),
    }
