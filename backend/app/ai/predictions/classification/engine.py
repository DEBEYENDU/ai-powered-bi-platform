"""Classification engine — Random Forest, XGBoost, LightGBM classifiers
for churn prediction, fraud detection, and categorical outcomes."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)


def _prepare_features(
    df: pd.DataFrame, target: str, features: list[str] | None = None
) -> tuple[pd.DataFrame, pd.Series]:
    """Prepare feature matrix and target vector for classification."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if features:
        cols = [c for c in features if c in df.columns]
    else:
        cols = [c for c in numeric_cols if c != target]

    if not cols:
        cols = [c for c in df.columns if c != target and df[c].dtype in ("int64", "float64")]

    X = df[cols].copy()
    y = df[target].copy()

    # Encode categorical targets if needed
    if y.dtype == object:
        unique_vals = y.unique()
        if len(unique_vals) == 2:
            y = (y == unique_vals[1]).astype(int)
        else:
            from sklearn.preprocessing import LabelEncoder
            le = LabelEncoder()
            y = pd.Series(le.fit_transform(y), name=target)

    # Fill NaN in X
    for col in X.columns:
        if X[col].dtype in ("int64", "float64"):
            X[col] = X[col].fillna(X[col].median())
        else:
            X[col] = X[col].fillna(0)

    return X, y


def train_classifier(
    df: pd.DataFrame,
    target: str,
    model_type: str = "random_forest",
    features: list[str] | None = None,
    test_size: float = 0.2,
    cv_folds: int = 5,
    **kwargs: Any,
) -> dict[str, Any]:
    """Train a classification model and return metrics + feature importances."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )
    from sklearn.model_selection import cross_val_score, train_test_split

    X, y = _prepare_features(df, target, features)
    if X.empty or len(y.unique()) < 2:
        return {"error": "Insufficient data or target has fewer than 2 classes"}

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

    # Select model
    if model_type == "xgboost":
        try:
            import xgboost as xgb
            model = xgb.XGBClassifier(
                n_estimators=kwargs.get("n_estimators", 100),
                max_depth=kwargs.get("max_depth", 6),
                learning_rate=kwargs.get("learning_rate", 0.1),
                random_state=42,
                eval_metric="logloss",
                use_label_encoder=False,
            )
        except ImportError:
            model = RandomForestClassifier(n_estimators=100, random_state=42)
    elif model_type == "lightgbm":
        try:
            import lightgbm as lgb
            model = lgb.LGBMClassifier(
                n_estimators=kwargs.get("n_estimators", 100),
                max_depth=kwargs.get("max_depth", 6),
                learning_rate=kwargs.get("learning_rate", 0.1),
                random_state=42,
                verbose=-1,
            )
        except ImportError:
            model = RandomForestClassifier(n_estimators=100, random_state=42)
    elif model_type == "logistic":
        model = LogisticRegression(max_iter=1000, random_state=42)
    else:
        model = RandomForestClassifier(
            n_estimators=kwargs.get("n_estimators", 100),
            max_depth=kwargs.get("max_depth", 10),
            random_state=42,
        )

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

    # Metrics
    precision = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    recall = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    try:
        roc = roc_auc_score(y_test, y_proba)
    except ValueError:
        roc = 0.0

    # Cross-validation
    try:
        cv_scores = cross_val_score(model, X, y, cv=min(cv_folds, len(y)), scoring="f1_weighted")
        cv_mean = float(np.mean(cv_scores))
        cv_std = float(np.std(cv_scores))
    except Exception:
        cv_mean = 0.0
        cv_std = 0.0

    # Feature importances
    importances: list[dict[str, Any]] = []
    if hasattr(model, "feature_importances_"):
        imp = model.feature_importances_
        for fname, fval in zip(X.columns, imp, strict=False):
            importances.append({"feature": fname, "importance": round(float(fval), 4)})
        importances.sort(key=lambda x: x["importance"], reverse=True)
    elif hasattr(model, "coef_"):
        coef = np.abs(model.coef_[0]) if model.coef_.ndim > 1 else np.abs(model.coef_)
        for fname, fval in zip(X.columns, coef, strict=False):
            importances.append({"feature": fname, "importance": round(float(fval), 4)})
        importances.sort(key=lambda x: x["importance"], reverse=True)

    return {
        "model_type": model_type,
        "metrics": {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "roc_auc": round(roc, 4),
            "cross_val_score": round(cv_mean, 4),
            "cross_val_std": round(cv_std, 4),
        },
        "feature_importances": importances[:20],
        "feature_names": list(X.columns),
        "n_classes": len(y.unique()),
        "class_distribution": {str(k): int(v) for k, v in y.value_counts().items()},
    }


def predict_classification(
    model: Any,
    df: pd.DataFrame,
    features: list[str] | None = None,
) -> dict[str, Any]:
    """Make predictions with a trained classifier."""
    X, _ = _prepare_features(df, "dummy" if "dummy" in df.columns else df.columns[0], features)

    if hasattr(model, "predict"):
        preds = model.predict(X)
        proba = model.predict_proba(X) if hasattr(model, "predict_proba") else None

        return {
            "predictions": preds.tolist(),
            "probabilities": proba.tolist() if proba is not None else None,
            "n_predictions": len(preds),
        }

    return {"error": "Model does not support prediction"}
