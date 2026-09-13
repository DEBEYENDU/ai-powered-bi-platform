"""AI Predictions router — all API endpoints for forecasting and predictive analytics."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.ai.predictions.schemas import (
    ModelComparisonRequest,
    MonitorRequest,
    PredictionChatRequest,
    PredictRequest,
    TrainModelRequest,
    WhatIfRequest,
)
from app.ai.predictions.services import ai_service, orchestrator

predictions_router = APIRouter(prefix="/ai/predictions", tags=["AI Predictions"])


# ---------------------------------------------------------------------------
# Main prediction endpoint
# ---------------------------------------------------------------------------


@predictions_router.post("/predict")
async def predict(request: PredictRequest) -> dict[str, Any]:
    """Generate predictions — auto-selects best model based on data."""
    result = await orchestrator.predict(request)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------


@predictions_router.post("/train")
async def train_model(request: TrainModelRequest) -> dict[str, Any]:
    """Train and evaluate a specific model."""
    result = await orchestrator.train_model(request)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Model comparison
# ---------------------------------------------------------------------------


@predictions_router.post("/compare")
async def compare_models(request: ModelComparisonRequest) -> dict[str, Any]:
    """Compare multiple models on the same dataset."""
    try:
        from app.ai.predictions.classification.engine import train_classifier
        from app.ai.predictions.regression.engine import train_regressor
        from app.ai.predictions.services.data_service import detect_target_type, load_dataset

        df = load_dataset(request.dataset_id)
        target_type = detect_target_type(df, request.target)

        models_to_try = request.model_types or ["random_forest", "xgboost", "lightgbm", "linear"]
        results: list[dict[str, Any]] = []

        for model_type in models_to_try:
            try:
                if target_type == "classification":
                    result = train_classifier(
                        df, request.target, model_type.value, request.features
                    )
                else:
                    result = train_regressor(df, request.target, model_type.value, request.features)
                if "error" not in result:
                    results.append(result)
            except Exception:
                continue

        if not results:
            return {"success": False, "error": "All models failed"}

        # Sort by primary metric
        metric = request.metric
        if target_type == "classification":
            results.sort(key=lambda r: r.get("metrics", {}).get("f1", 0), reverse=True)
        else:
            results.sort(key=lambda r: r.get("metrics", {}).get("rmse", float("inf")))

        best = results[0].get("model_type", "")

        return {
            "success": True,
            "models": results,
            "best_model": best,
            "comparison_metric": metric,
        }
    except FileNotFoundError:
        return {"success": False, "error": "Dataset not found"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# What-if analysis
# ---------------------------------------------------------------------------


@predictions_router.post("/whatif")
async def whatif_analysis(request: WhatIfRequest) -> dict[str, Any]:
    """Perform what-if analysis by simulating variable changes."""
    try:
        from app.ai.predictions.services.data_service import load_dataset

        df = load_dataset(request.dataset_id)
        current_state = f"Target: {request.target}, Rows: {len(df)}, Columns: {list(df.columns)}"
        variables_str = "\n".join(f"  {k}: {v}" for k, v in request.variables.items())

        result = await ai_service.whatif_analysis(
            current_state=current_state,
            scenario_description=f"Simulate changes to predict impact on {request.target}",
            variables=variables_str,
            target=request.target,
            horizon=request.horizon,
        )
        return {"success": True, **result}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Root cause analysis
# ---------------------------------------------------------------------------


@predictions_router.post("/root-cause")
async def root_cause(body: dict[str, Any]) -> dict[str, Any]:
    """Explain why predictions changed."""
    try:
        result = await ai_service.root_cause_analysis(
            prediction_history=body.get("prediction_history", "No history"),
            feature_importances=body.get("feature_importances", "No importances"),
            data_changes=body.get("data_changes", "No changes detected"),
        )
        return {"success": True, **result}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------


@predictions_router.post("/monitor")
async def monitor_model(request: MonitorRequest) -> dict[str, Any]:
    """Monitor a model for data/prediction drift."""
    result = await orchestrator.monitor_model(request)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Prediction chat
# ---------------------------------------------------------------------------


@predictions_router.post("/chat")
async def prediction_chat(request: PredictionChatRequest) -> dict[str, Any]:
    """Ask AI a question about a prediction."""
    result = await orchestrator.chat_about_prediction(request)
    return result


# ---------------------------------------------------------------------------
# Alert rules
# ---------------------------------------------------------------------------


@predictions_router.get("/alerts")
async def list_alert_rules() -> dict[str, Any]:
    """List active prediction alert rules."""
    return {
        "alerts": [
            {
                "id": "alert_1",
                "type": "revenue_decline",
                "condition": "predicted_revenue < current_revenue * 0.9",
                "severity": "high",
                "enabled": True,
            },
            {
                "id": "alert_2",
                "type": "inventory_shortage",
                "condition": "predicted_demand > current_inventory * 1.2",
                "severity": "critical",
                "enabled": True,
            },
            {
                "id": "alert_3",
                "type": "high_churn_risk",
                "condition": "churn_probability > 0.7",
                "severity": "high",
                "enabled": True,
            },
        ],
        "count": 3,
    }
