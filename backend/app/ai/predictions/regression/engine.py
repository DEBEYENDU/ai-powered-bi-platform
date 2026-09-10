"""Regression engine — Linear, Random Forest, XGBoost, LightGBM regressors
for predicting continuous values like revenue, sales, expenses."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)


def _prepare_features(
    df: pd.DataFrame, target: str, features: list[str] | None = None
) -> tuple[pd.DataFrame, pd.Series]:
    """Prepare feature matrix and target vector for regression."""
    if features:
        cols = [c for c in features if c in df.columns]
    else:
        cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != target]

    if not cols:
        cols = [c for c in df.columns if c != target and df[c].dtype in ("int64", "float64")]

    X = df[cols].copy()
    y = pd.to_numeric(df[target], errors="coerce").dropna()

    # Align X with y
    common_idx = X.index.intersection(y.index)
    X = X.loc[common_idx]
    y = y.loc[common_idx]

    # Fill NaN
    for col in X.columns:
        if X[col].dtype in ("int64", "float64"):
            X[col] = X[col].fillna(X[col].median())
        else:
            X[col] = X[col].fillna(0)

    return X, y


def train_regressor(
    df: pd.DataFrame,
    target: str,
    model_type: str = "random_forest",
    features: list[str] | None = None,
    test_size: float = 0.2,
    cv_folds: int = 5,
    **kwargs: Any,
) -> dict[str, Any]:
    """Train a regression model and return metrics + feature importances."""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import cross_val_score, train_test_split

    X, y = _prepare_features(df, target, features)
    if X.empty or len(y) < 5:
        return {"error": "Insufficient data for regression"}

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

    if model_type == "xgboost":
        try:
            import xgboost as xgb
            model = xgb.XGBRegressor(
                n_estimators=kwargs.get("n_estimators", 100),
                max_depth=kwargs.get("max_depth", 6),
                learning_rate=kwargs.get("learning_rate", 0.1),
                random_state=42,
            )
        except ImportError:
            model = RandomForestRegressor(n_estimators=100, random_state=42)
    elif model_type == "lightgbm":
        try:
            import lightgbm as lgb
            model = lgb.LGBMRegressor(
                n_estimators=kwargs.get("n_estimators", 100),
                max_depth=kwargs.get("max_depth", 6),
                learning_rate=kwargs.get("learning_rate", 0.1),
                random_state=42,
                verbose=-1,
            )
        except ImportError:
            model = RandomForestRegressor(n_estimators=100, random_state=42)
    elif model_type == "ridge":
        model = Ridge(alpha=kwargs.get("alpha", 1.0))
    elif model_type == "linear":
        model = LinearRegression()
    else:
        model = RandomForestRegressor(
            n_estimators=kwargs.get("n_estimators", 100),
            max_depth=kwargs.get("max_depth", 10),
            random_state=42,
        )

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    mape = float(np.mean(np.abs((y_test - y_pred) / np.where(y_test == 0, 1, y_test)))) * 100
    r2 = r2_score(y_test, y_pred)

    # Cross-validation
    try:
        cv_scores = cross_val_score(model, X, y, cv=min(cv_folds, max(2, len(y) // 5)), scoring="r2")
        cv_mean = float(np.mean(cv_scores))
        cv_std = float(np.std(cv_scores))
    except Exception:
        cv_mean = 0.0
        cv_std = 0.0

    # Feature importances
    importances: list[dict[str, Any]] = []
    if hasattr(model, "feature_importances_"):
        for fname, fval in zip(X.columns, model.feature_importances_, strict=False):
            importances.append({"feature": fname, "importance": round(float(fval), 4)})
        importances.sort(key=lambda x: x["importance"], reverse=True)
    elif hasattr(model, "coef_"):
        coef = np.abs(model.coef_)
        for fname, fval in zip(X.columns, coef, strict=False):
            importances.append({"feature": fname, "importance": round(float(fval), 4)})
        importances.sort(key=lambda x: x["importance"], reverse=True)

    return {
        "model_type": model_type,
        "metrics": {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "mape": round(mape, 4),
            "r2": round(r2, 4),
            "cross_val_score": round(cv_mean, 4),
            "cross_val_std": round(cv_std, 4),
        },
        "feature_importances": importances[:20],
        "feature_names": list(X.columns),
        "n_samples": len(X),
        "n_features": X.shape[1],
    }


def predict_regression(
    model: Any,
    df: pd.DataFrame,
    features: list[str] | None = None,
) -> dict[str, Any]:
    """Make predictions with a trained regressor."""
    X, _ = _prepare_features(df, "dummy" if "dummy" in df.columns else df.columns[0], features)

    if hasattr(model, "predict"):
        preds = model.predict(X)
        return {
            "predictions": preds.tolist(),
            "n_predictions": len(preds),
        }

    return {"error": "Model does not support prediction"}
