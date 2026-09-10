"""Request / response schemas for the AI Predictions platform."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# --- Enums ---


class PredictionType(str, Enum):
    FORECAST = "forecast"
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    ANOMALY = "anomaly"
    CLUSTERING = "clustering"


class ModelType(str, Enum):
    LINEAR_REGRESSION = "linear_regression"
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    ARIMA = "arima"
    SARIMA = "sarima"
    PROPHET = "prophet"
    LSTM = "lstm"
    TRANSFORMER = "transformer"
    ISOLATION_FOREST = "isolation_forest"
    KMEANS = "kmeans"
    AUTO_ML = "auto_ml"


class TrendDirection(str, Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class ModelStatus(str, Enum):
    TRAINING = "training"
    READY = "ready"
    FAILED = "failed"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class DriftType(str, Enum):
    DATA_DRIFT = "data_drift"
    MODEL_DRIFT = "model_drift"
    PREDICTION_DRIFT = "prediction_drift"
    CONCEPT_DRIFT = "concept_drift"


class ScenarioType(str, Enum):
    INCREASE_BUDGET = "increase_budget"
    REDUCE_EXPENSES = "reduce_expenses"
    HIRE_EMPLOYEES = "hire_employees"
    INCREASE_PRICES = "increase_prices"
    LAUNCH_PRODUCT = "launch_product"
    EXPAND_REGION = "expand_region"
    CUSTOM = "custom"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# --- Request schemas ---


class PredictRequest(BaseModel):
    dataset_id: str
    target: str = Field(..., min_length=1)
    horizon: str = "30_days"
    model_type: ModelType | None = None
    features: list[str] | None = None
    confidence_level: float = Field(default=0.95, ge=0.5, le=0.99)
    include_explanation: bool = True
    include_recommendations: bool = True


class TrainModelRequest(BaseModel):
    dataset_id: str
    target: str = Field(..., min_length=1)
    model_type: ModelType = ModelType.AUTO_ML
    features: list[str] | None = None
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    test_size: float = Field(default=0.2, ge=0.1, le=0.5)
    cross_validation_folds: int = Field(default=5, ge=2, le=10)
    retrain: bool = False


class ScenarioRequest(BaseModel):
    dataset_id: str
    target: str
    base_prediction_id: str = ""
    scenarios: list[dict[str, Any]] = Field(default_factory=list)
    horizon: str = "30_days"


class WhatIfRequest(BaseModel):
    dataset_id: str
    target: str
    variables: dict[str, Any] = Field(default_factory=dict)
    horizon: str = "30_days"


class ModelComparisonRequest(BaseModel):
    dataset_id: str
    target: str
    model_types: list[ModelType] = Field(default_factory=list)
    features: list[str] | None = None
    metric: str = "rmse"


class RetrainRequest(BaseModel):
    model_id: str
    reason: str = ""


class PredictionChatRequest(BaseModel):
    prediction_id: str
    question: str = Field(..., min_length=1)


class MonitorRequest(BaseModel):
    model_id: str
    lookback_days: int = Field(default=30, ge=1, le=365)


# --- Nested models ---


class ForecastPoint(BaseModel):
    date: str
    value: float
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    best_case: float = 0.0
    worst_case: float = 0.0


class ModelMetrics(BaseModel):
    mae: float = 0.0
    rmse: float = 0.0
    mape: float = 0.0
    r2: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    roc_auc: float = 0.0
    cross_val_score: float = 0.0
    cross_val_std: float = 0.0


class FeatureImportance(BaseModel):
    feature: str
    importance: float
    direction: str = ""


class Explainability(BaseModel):
    feature_importances: list[FeatureImportance] = Field(default_factory=list)
    shap_values: list[dict[str, Any]] = Field(default_factory=list)
    business_interpretation: str = ""
    top_factors: list[str] = Field(default_factory=list)


class BusinessRecommendation(BaseModel):
    category: str
    recommendation: str
    impact: str
    confidence: str
    priority: str = "medium"


class DriftAlert(BaseModel):
    drift_type: str
    severity: str
    feature: str = ""
    description: str = ""
    detected_at: str = ""
    recommended_action: str = ""


class ScenarioResult(BaseModel):
    scenario_name: str
    scenario_type: str
    predicted_impact: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    recommendation: str = ""


class ModelVersion(BaseModel):
    version: int
    model_type: str
    metrics: ModelMetrics
    created_at: str
    status: str
    is_active: bool = False


class ModelInfo(BaseModel):
    id: str
    name: str
    model_type: str
    target: str
    dataset_id: str
    status: str
    metrics: ModelMetrics = Field(default_factory=ModelMetrics)
    feature_names: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    versions: list[ModelVersion] = Field(default_factory=list)


class PredictionResult(BaseModel):
    prediction_id: str = ""
    dataset_id: str = ""
    target: str
    model_used: str
    model_type: str
    horizon: str
    predictions: list[ForecastPoint] = Field(default_factory=list)
    overall_confidence: float = 0.0
    trend: str = "stable"
    growth_percentage: float = 0.0
    risk_score: float = 0.0
    metrics: ModelMetrics = Field(default_factory=ModelMetrics)
    explainability: Explainability = Field(default_factory=Explainability)
    recommendations: list[BusinessRecommendation] = Field(default_factory=list)
    created_at: str = ""
    error: str | None = None


# --- Response schemas ---


class PredictionResponse(BaseModel):
    success: bool
    result: PredictionResult | None = None
    error: str | None = None


class TrainResponse(BaseModel):
    success: bool
    model_id: str = ""
    model_type: str = ""
    metrics: ModelMetrics = Field(default_factory=ModelMetrics)
    training_time_ms: float = 0.0
    error: str | None = None


class CompareResponse(BaseModel):
    success: bool
    models: list[dict[str, Any]] = Field(default_factory=list)
    best_model: str = ""
    comparison_metric: str = ""
    error: str | None = None


class ScenarioResponse(BaseModel):
    success: bool
    scenarios: list[ScenarioResult] = Field(default_factory=list)
    base_prediction: PredictionResult | None = None
    error: str | None = None


class MonitorResponse(BaseModel):
    success: bool
    model_id: str
    data_drift: list[DriftAlert] = Field(default_factory=list)
    model_drift: list[DriftAlert] = Field(default_factory=list)
    prediction_drift: list[DriftAlert] = Field(default_factory=list)
    overall_health: str = "healthy"
    retraining_recommended: bool = False
    error: str | None = None


class ModelsListResponse(BaseModel):
    success: bool
    models: list[ModelInfo] = Field(default_factory=list)
    count: int = 0
    error: str | None = None


class PredictionsListResponse(BaseModel):
    success: bool
    predictions: list[PredictionResult] = Field(default_factory=list)
    count: int = 0
    error: str | None = None
