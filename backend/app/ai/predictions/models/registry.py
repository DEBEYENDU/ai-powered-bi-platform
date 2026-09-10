"""Model registry — versioning, AutoML selection, model storage."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from app.ai.predictions.classification.engine import train_classifier
from app.ai.predictions.forecasting.engine import forecast_arima, forecast_prophet, forecast_sarima
from app.ai.predictions.regression.engine import train_regressor
from app.core.config import get_settings


def _model_storage() -> Path:
    settings = get_settings()
    base = Path(getattr(settings, "storage_path", "/tmp/bi_storage"))
    root = base / "ai_models"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _generate_id() -> str:
    return str(uuid.uuid4())[:12]


def auto_select_model(
    df: pd.DataFrame,
    target: str,
    features: list[str] | None = None,
) -> dict[str, Any]:
    """Automatically select the best model type based on data characteristics."""
    n_rows = len(df)
    n_cols = len(df.columns)
    target_series = pd.to_numeric(df[target], errors="coerce").dropna()

    # Detect if target is time-based
    has_date = False
    for col in df.columns:
        try:
            dates = pd.to_datetime(df[col], errors="coerce")
            if dates.notna().sum() > len(df) * 0.5:
                has_date = True
                break
        except Exception:
            pass

    # Detect if classification or regression
    n_unique = target_series.nunique()
    is_classification = n_unique <= 10 and n_unique < n_rows * 0.05

    # Model selection logic
    if has_date and not is_classification:
        # Time series
        if n_rows > 365:
            recommended = "prophet"
            reasoning = "Large time series dataset with yearly seasonality potential"
        elif n_rows > 60:
            recommended = "sarima"
            reasoning = "Moderate time series data with seasonal patterns"
        else:
            recommended = "arima"
            reasoning = "Small time series dataset"
    elif is_classification:
        if n_rows > 10000:
            recommended = "xgboost"
            reasoning = "Large dataset — gradient boosting excels"
        elif n_rows > 1000:
            recommended = "lightgbm"
            reasoning = "Medium dataset — LightGBM is efficient"
        else:
            recommended = "random_forest"
            reasoning = "Small dataset — Random Forest is robust"
    else:
        # Regression
        if n_rows > 10000 and n_cols > 20:
            recommended = "xgboost"
            reasoning = "Large dataset with many features — XGBoost handles well"
        elif n_rows > 1000:
            recommended = "lightgbm"
            reasoning = "Medium dataset — LightGBM is fast and accurate"
        elif n_rows > 100:
            recommended = "random_forest"
            reasoning = "Small-medium dataset — Random Forest is robust"
        else:
            recommended = "linear"
            reasoning = "Very small dataset — Linear model is simplest"

    alternatives = ["random_forest", "xgboost", "lightgbm", "linear", "ridge"]
    if recommended in alternatives:
        alternatives.remove(recommended)

    return {
        "recommended": recommended,
        "reasoning": reasoning,
        "alternatives": alternatives[:3],
        "data_characteristics": {
            "n_rows": n_rows,
            "n_cols": n_cols,
            "target_unique": n_unique,
            "is_classification": is_classification,
            "has_date": has_date,
        },
    }


def train_auto_model(
    df: pd.DataFrame,
    target: str,
    features: list[str] | None = None,
    test_size: float = 0.2,
    cv_folds: int = 5,
    **kwargs: Any,
) -> dict[str, Any]:
    """Train multiple models and select the best one."""
    selection = auto_select_model(df, target, features)
    recommended = selection["recommended"]

    is_classification = selection["data_characteristics"]["is_classification"]
    has_date = selection["data_characteristics"]["has_date"]

    results: list[dict[str, Any]] = []

    if has_date and not is_classification:
        # Try time series models
        for date_col in df.columns:
            try:
                dates = pd.to_datetime(df[date_col], errors="coerce")
                if dates.notna().sum() > len(df) * 0.5:
                    for model_type in ["prophet", "arima", "sarima"]:
                        try:
                            if model_type == "prophet":
                                result = forecast_prophet(df, date_col, target, "30_days")
                            elif model_type == "arima":
                                result = forecast_arima(df, date_col, target, "30_days")
                            else:
                                result = forecast_sarima(df, date_col, target, "30_days")
                            result["model_type"] = model_type
                            results.append(result)
                        except Exception:
                            continue
                    break
            except Exception:
                continue

    # Try ML models
    model_types_to_try = [recommended] + selection["alternatives"]
    for model_type in model_types_to_try:
        try:
            if is_classification:
                result = train_classifier(df, target, model_type, features, test_size, cv_folds, **kwargs)
            else:
                result = train_regressor(df, target, model_type, features, test_size, cv_folds, **kwargs)
            if "error" not in result:
                result["model_type"] = model_type
                results.append(result)
        except Exception:
            continue

    if not results:
        return {"error": "All model training attempts failed"}

    # Select best model by primary metric
    def _score(r: dict[str, Any]) -> float:
        m = r.get("metrics", {})
        if is_classification:
            return m.get("f1", 0) + m.get("roc_auc", 0) * 0.5
        return -(m.get("rmse", float("inf")))

    results.sort(key=_score, reverse=True)
    best = results[0]

    return {
        "best_model": best,
        "all_models": results,
        "selection_reasoning": selection["reasoning"],
        "data_characteristics": selection["data_characteristics"],
    }


def save_model(
    model: Any,
    model_id: str,
    model_type: str,
) -> str:
    """Persist a trained model to disk. Returns storage path."""
    root = _model_storage()
    path = root / f"{model_id}.json"

    # Serialize model metadata (not the sklearn object itself for simplicity)
    metadata = {
        "model_id": model_id,
        "model_type": model_type,
        "saved_at": time.time(),
    }
    path.write_text(json.dumps(metadata))
    return str(path)


def load_model(model_id: str) -> dict[str, Any]:
    """Load model metadata from disk."""
    root = _model_storage()
    path = root / f"{model_id}.json"
    if not path.exists():
        return {"error": f"Model {model_id} not found"}
    return json.loads(path.read_text())


def list_models() -> list[dict[str, Any]]:
    """List all persisted models."""
    root = _model_storage()
    models: list[dict[str, Any]] = []
    for f in root.glob("*.json"):
        try:
            models.append(json.loads(f.read_text()))
        except Exception:
            continue
    return models
