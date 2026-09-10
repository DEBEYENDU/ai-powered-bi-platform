"""Data service — loads datasets from the data engineering storage layer."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core.config import get_settings


def _versions_root() -> Path:
    settings = get_settings()
    base = Path(getattr(settings, "storage_path", "/tmp/bi_storage"))
    root = base / "de_versions"
    root.mkdir(parents=True, exist_ok=True)
    return root


def load_dataset(dataset_id: str, version: str = "v1") -> pd.DataFrame:
    """Load a dataset by ID from the data engineering storage."""
    root = _versions_root()
    fname = f"{dataset_id}_{version}.parquet"
    path = root / fname
    if path.exists():
        return pd.read_parquet(path)

    # Try clean version
    clean_fname = f"{dataset_id}_clean_{version}.parquet"
    clean_path = root / clean_fname
    if clean_path.exists():
        return pd.read_parquet(clean_path)

    # Try transform version
    t_fname = f"{dataset_id}_t_{version}.parquet"
    t_path = root / t_fname
    if t_path.exists():
        return pd.read_parquet(t_path)

    raise FileNotFoundError(f"Dataset {dataset_id} not found in storage")


def detect_target_type(df: pd.DataFrame, target: str) -> str:
    """Detect whether target is regression, classification, or time series."""
    if target not in df.columns:
        return "regression"

    series = df[target]
    n_unique = series.nunique()

    # Check if date column exists
    has_date = False
    for col in df.columns:
        try:
            dates = pd.to_datetime(df[col], errors="coerce")
            if dates.notna().sum() > len(df) * 0.5:
                has_date = True
                break
        except Exception:
            pass

    if has_date:
        return "time_series"

    if n_unique <= 10 and n_unique < len(df) * 0.05:
        return "classification"

    return "regression"


def prepare_features(
    df: pd.DataFrame,
    target: str,
    features: list[str] | None = None,
) -> tuple[pd.DataFrame, str]:
    """Prepare features for modeling, auto-detecting the target type."""
    target_type = detect_target_type(df, target)

    if features:
        feature_cols = [c for c in features if c in df.columns and c != target]
    else:
        # Auto-select features
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        feature_cols = [c for c in numeric_cols if c != target]

        # Add important categorical columns (low cardinality)
        for col in df.select_dtypes(include=["object", "category"]).columns:
            if col != target and df[col].nunique() < 20:
                # One-hot encode
                dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
                df = pd.concat([df, dummies], axis=1)
                feature_cols.extend(dummies.columns.tolist())

    if not feature_cols:
        feature_cols = [c for c in df.columns if c != target and df[c].dtype in ("int64", "float64")]

    return df, target_type
