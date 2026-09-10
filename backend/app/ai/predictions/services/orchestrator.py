"""Orchestrator — ties together forecasting, classification, regression,
evaluation, recommendations, monitoring, and AI into a unified workflow."""

from __future__ import annotations

import time
import uuid
from typing import Any

import numpy as np
import pandas as pd

from app.ai.predictions.classification.engine import train_classifier
from app.ai.predictions.evaluation.metrics import (
    compute_time_series_metrics,
)
from app.ai.predictions.forecasting.engine import (
    forecast_arima,
    forecast_prophet,
    forecast_sarima,
)
from app.ai.predictions.models.registry import train_auto_model
from app.ai.predictions.recommendations.engine import (
    assess_risk,
)
from app.ai.predictions.regression.engine import train_regressor
from app.ai.predictions.schemas import (
    BusinessRecommendation,
    Explainability,
    FeatureImportance,
    ForecastPoint,
    ModelMetrics,
    MonitorRequest,
    MonitorResponse,
    PredictionResult,
    PredictRequest,
    PredictResponse,
    TrainModelRequest,
    TrainResponse,
)
from app.ai.predictions.services import ai_service, data_service


async def predict(request: PredictRequest) -> PredictResponse:
    """Main prediction endpoint — auto-select model, train, forecast, explain."""
    time.perf_counter()
    try:
        df = data_service.load_dataset(request.dataset_id)
        target_type = data_service.detect_target_type(df, request.target)

        if target_type == "time_series":
            result = await _forecast_time_series(df, request)
        elif target_type == "classification":
            result = await _predict_classification(df, request)
        else:
            result = await _predict_regression(df, request)

        result.dataset_id = request.dataset_id
        result.target = request.target
        result.horizon = request.horizon

        return PredictResponse(success=True, result=result)
    except FileNotFoundError:
        return PredictResponse(success=False, error="Dataset not found")
    except Exception as exc:
        return PredictResponse(success=False, error=str(exc))


async def _forecast_time_series(
    df: pd.DataFrame, request: PredictRequest
) -> PredictionResult:
    """Handle time series forecasting."""
    # Find date column
    date_col = None
    for col in df.columns:
        try:
            dates = pd.to_datetime(df[col], errors="coerce")
            if dates.notna().sum() > len(df) * 0.5:
                date_col = col
                break
        except Exception:
            continue

    if not date_col:
        date_col = df.columns[0]

    model_type = request.model_type.value if request.model_type else "prophet"

    # Try forecasting
    if model_type == "prophet":
        result = forecast_prophet(df, date_col, request.target, request.horizon, request.confidence_level)
    elif model_type == "sarima":
        result = forecast_sarima(df, date_col, request.target, request.horizon, request.confidence_level)
    else:
        result = forecast_arima(df, date_col, request.target, request.horizon, request.confidence_level)

    predictions = [ForecastPoint(**p) for p in result.get("predictions", [])]

    # Metrics
    if len(predictions) >= 2:
        values = [p.value for p in predictions]
        metrics = compute_time_series_metrics(values[:-1], values[1:])
    else:
        metrics = {}

    # Risk assessment
    risk = assess_risk(
        [p.model_dump() for p in predictions],
        result.get("trend", "stable"),
        metrics,
    )

    # Feature importance (not available for time series, provide trend info)
    explainability = Explainability(
        feature_importances=[],
        business_interpretation=f"Forecast shows {result.get('trend', 'stable')} trend with {result.get('growth_percentage', 0):.1f}% growth",
        top_factors=["historical_trend", "seasonality", "recent_values"],
    )

    # AI recommendations
    forecast_summary = "\n".join([
        f"  {p.date}: {p.value:.2f} [{p.lower_bound:.2f}-{p.upper_bound:.2f}]"
        for p in predictions[:10]
    ])

    ai_recs = await ai_service.generate_business_recommendations(
        target=request.target,
        trend=result.get("trend", "stable"),
        growth_pct=result.get("growth_percentage", 0),
        risk_score=risk["risk_score"],
        horizon=request.horizon,
        forecast_summary=forecast_summary,
        top_factors="historical trend, seasonality, recent values",
    )
    recommendations = [BusinessRecommendation(**r) for r in ai_recs]

    return PredictionResult(
        prediction_id=str(uuid.uuid4())[:12],
        model_used="auto",
        model_type=result.get("model_type", "prophet"),
        predictions=predictions,
        overall_confidence=result.get("confidence", 0.95),
        trend=result.get("trend", "stable"),
        growth_percentage=result.get("growth_percentage", 0),
        risk_score=risk["risk_score"],
        metrics=ModelMetrics(**{k: v for k, v in metrics.items() if k in ModelMetrics.model_fields}),
        explainability=explainability,
        recommendations=recommendations,
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )


async def _predict_regression(
    df: pd.DataFrame, request: PredictRequest
) -> PredictionResult:
    """Handle regression prediction."""
    model_type = request.model_type.value if request.model_type else "auto"

    if model_type == "auto":
        result = train_auto_model(df, request.target, request.features)
        if "error" in result:
            return PredictionResult(
                target=request.target,
                model_used="failed",
                model_type="",
                error=result["error"],
            )
        best = result["best_model"]
    else:
        best = train_regressor(df, request.target, model_type, request.features)
        if "error" in best:
            return PredictionResult(
                target=request.target,
                model_used="failed",
                model_type=model_type,
                error=best["error"],
            )

    metrics_data = best.get("metrics", {})
    importances = [
        FeatureImportance(feature=f["feature"], importance=f["importance"])
        for f in best.get("feature_importances", [])[:10]
    ]

    # Generate predictions (next N periods)
    horizon_val = int(request.horizon.split("_")[0]) if "_" in request.horizon else 30
    last_val = df[request.target].dropna().iloc[-1] if request.target in df.columns else 0

    predictions: list[ForecastPoint] = []
    trend_data = best.get("feature_importances", [])
    avg_importance = np.mean([f["importance"] for f in trend_data]) if trend_data else 0

    for i in range(1, horizon_val + 1):
        # Simple extrapolation based on model metrics
        noise = np.random.normal(0, metrics_data.get("rmse", 0) * 0.1)
        val = last_val * (1 + (i * avg_importance * 0.01)) + noise
        margin = metrics_data.get("rmse", 0) * (1 + i * 0.02)
        predictions.append(ForecastPoint(
            date=f"day_{i}",
            value=round(float(val), 4),
            lower_bound=round(float(val - margin), 4),
            upper_bound=round(float(val + margin), 4),
            best_case=round(float(val + margin * 1.5), 4),
            worst_case=round(float(val - margin * 1.5), 4),
        ))

    growth_pct = 0.0
    trend = "stable"
    if len(predictions) >= 2:
        growth_pct = ((predictions[-1].value - predictions[0].value) / max(abs(predictions[0].value), 1e-10)) * 100
        trend = "increasing" if growth_pct > 1 else "decreasing" if growth_pct < -1 else "stable"

    risk = assess_risk(
        [p.model_dump() for p in predictions], trend, metrics_data
    )

    explainability = Explainability(
        feature_importances=importances,
        business_interpretation=f"Model explains {metrics_data.get('r2', 0):.1%} of variance in {request.target}",
        top_factors=[f.feature for f in importances[:5]],
    )

    return PredictionResult(
        prediction_id=str(uuid.uuid4())[:12],
        model_used=best.get("model_type", "unknown"),
        model_type=best.get("model_type", "unknown"),
        predictions=predictions,
        overall_confidence=0.95,
        trend=trend,
        growth_percentage=round(growth_pct, 2),
        risk_score=risk["risk_score"],
        metrics=ModelMetrics(**{k: v for k, v in metrics_data.items() if k in ModelMetrics.model_fields}),
        explainability=explainability,
        recommendations=[],
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )


async def _predict_classification(
    df: pd.DataFrame, request: PredictRequest
) -> PredictionResult:
    """Handle classification prediction."""
    model_type = request.model_type.value if request.model_type else "random_forest"

    result = train_classifier(df, request.target, model_type, request.features)
    if "error" in result:
        return PredictionResult(
            target=request.target,
            model_used="failed",
            model_type=model_type,
            error=result["error"],
        )

    metrics_data = result.get("metrics", {})
    importances = [
        FeatureImportance(feature=f["feature"], importance=f["importance"])
        for f in result.get("feature_importances", [])[:10]
    ]

    explainability = Explainability(
        feature_importances=importances,
        business_interpretation=f"Classifier achieves {metrics_data.get('accuracy', 0):.1%} accuracy",
        top_factors=[f.feature for f in importances[:5]],
    )

    return PredictionResult(
        prediction_id=str(uuid.uuid4())[:12],
        model_used=result.get("model_type", model_type),
        model_type=result.get("model_type", model_type),
        predictions=[],
        overall_confidence=metrics_data.get("accuracy", 0),
        trend="stable",
        growth_percentage=0,
        risk_score=0,
        metrics=ModelMetrics(**{k: v for k, v in metrics_data.items() if k in ModelMetrics.model_fields}),
        explainability=explainability,
        recommendations=[],
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )


async def train_model(request: TrainModelRequest) -> TrainResponse:
    """Train and register a model."""
    t0 = time.perf_counter()
    try:
        df = data_service.load_dataset(request.dataset_id)
        target_type = data_service.detect_target_type(df, request.target)

        if target_type == "time_series":
            return TrainResponse(
                success=False,
                error="Use /predict endpoint for time series models",
            )
        elif target_type == "classification":
            result = train_classifier(
                df, request.target, request.model_type.value,
                request.features, request.test_size,
                request.cross_validation_folds,
            )
        else:
            result = train_regressor(
                df, request.target, request.model_type.value,
                request.features, request.test_size,
                request.cross_validation_folds,
            )

        if "error" in result:
            return TrainResponse(success=False, error=result["error"])

        model_id = str(uuid.uuid4())[:12]
        metrics_data = result.get("metrics", {})

        return TrainResponse(
            success=True,
            model_id=model_id,
            model_type=result.get("model_type", request.model_type.value),
            metrics=ModelMetrics(**{k: v for k, v in metrics_data.items() if k in ModelMetrics.model_fields}),
            training_time_ms=round((time.perf_counter() - t0) * 1000, 1),
        )
    except FileNotFoundError:
        return TrainResponse(success=False, error="Dataset not found")
    except Exception as exc:
        return TrainResponse(success=False, error=str(exc))


async def monitor_model(request: MonitorRequest) -> MonitorResponse:
    """Monitor a model for drift."""
    try:
        # Simulate monitoring with synthetic data
        # In production, load actual reference and current data
        return MonitorResponse(
            success=True,
            model_id=request.model_id,
            overall_health="healthy",
            retraining_recommended=False,
        )
    except Exception as exc:
        return MonitorResponse(
            success=False,
            model_id=request.model_id,
            error=str(exc),
        )


async def chat_about_prediction(request: Any) -> dict[str, Any]:
    """Chat about a specific prediction."""
    return await ai_service.prediction_chat(
        target=getattr(request, "target", "value"),
        model_type="auto",
        trend="stable",
        confidence=0.95,
        horizon="30_days",
        forecast_summary="No prediction loaded",
        explainability="No explanation available",
        question=request.question,
    )
