"""LLM prompt templates for prediction and forecasting tasks."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are a senior data scientist and predictive analytics expert embedded in an
AI-Powered Business Intelligence platform.  You analyse historical data, build
forecasts, explain predictions, and provide actionable business recommendations.
Always ground your analysis in the actual data statistics and model metrics provided.
Respond with structured JSON when requested."""

# ---------------------------------------------------------------------------
# Forecast explanation
# ---------------------------------------------------------------------------

FORECAST_EXPLANATION_PROMPT = """\
Analyse the following forecast results and provide a clear explanation.

TARGET: {target}
HORIZON: {horizon}
MODEL: {model_type}
CONFIDENCE: {confidence}
TREND: {trend}
GROWTH: {growth_pct}%

FORECAST VALUES (first 10):
{forecast_summary}

METRICS:
{metrics}

TASK:
1. Explain the forecast in plain business language
2. Identify the key drivers of the trend
3. Highlight any risks or opportunities
4. Provide 3 actionable recommendations
5. Rate the reliability of this forecast (low/medium/high)

Return JSON with keys: explanation, drivers, risks, opportunities, recommendations, reliability."""

# ---------------------------------------------------------------------------
# What-if analysis
# ---------------------------------------------------------------------------

WHATIF_PROMPT = """\
Perform a what-if analysis based on the following scenario.

CURRENT STATE:
{current_state}

SCENARIO: {scenario_description}
VARIABLES CHANGED:
{variables}

TASK:
Predict the impact of these changes on {target} over {horizon}.
For each variable:
1. Predicted impact direction (positive/negative)
2. Magnitude of change
3. Confidence level
4. Time to effect

Provide an overall predicted impact on the target variable.
Return JSON with: impacts, overall_impact, confidence, timeline, risks."""

# ---------------------------------------------------------------------------
# Root cause analysis
# ---------------------------------------------------------------------------

ROOT_CAUSE_PROMPT = """\
Explain why the prediction changed or what factors are most influential.

PREDICTION HISTORY:
{prediction_history}

FEATURE IMPORTANCES:
{feature_importances}

RECENT DATA CHANGES:
{data_changes}

TASK:
1. Identify the top 3 factors driving the prediction
2. Explain how each factor contributes
3. Quantify the contribution (percentage)
4. Provide business context for each factor
5. Recommend actions to influence the prediction

Return JSON with: factors (with feature, contribution_pct, explanation, business_context), actions."""

# ---------------------------------------------------------------------------
# Business recommendations
# ---------------------------------------------------------------------------

RECOMMENDATIONS_PROMPT = """\
Based on the following prediction, provide actionable business recommendations.

PREDICTION:
Target: {target}
Trend: {trend}
Growth: {growth_pct}%
Risk Score: {risk_score}
Horizon: {horizon}

FORECAST SUMMARY:
{forecast_summary}

TOP FACTORS:
{top_factors}

TASK:
Generate 5 specific, actionable recommendations:
1. Each must address a specific aspect (revenue, cost, risk, growth, operations)
2. Each must include expected impact
3. Each must include priority level (critical/high/medium/low)
4. Each must include confidence level
5. Each must include a specific action to take

Return JSON array of recommendations with: category, recommendation, impact, priority, confidence."""

# ---------------------------------------------------------------------------
# Anomaly explanation
# ---------------------------------------------------------------------------

ANOMALY_PROMPT = """\
Explain the detected anomalies and their business implications.

ANOMALIES DETECTED:
{anomalies}

HISTORICAL CONTEXT:
{historical_context}

TASK:
For each anomaly:
1. Explain what happened
2. Possible causes
3. Business impact (quantified if possible)
4. Recommended response
5. Whether it's likely to recur

Return JSON with: explanations, overall_assessment, response_plan."""

# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------

MODEL_SELECTION_PROMPT = """\
Recommend the best model for this prediction task.

DATA CHARACTERISTICS:
{data_characteristics}

TARGET: {target}
HISTORICAL PERFORMANCE:
{historical_performance}

TASK:
Based on the data characteristics, recommend the best model type.
Consider:
1. Data size (rows, features)
2. Time series vs tabular
3. Seasonality patterns
4. Feature types (numeric, categorical)
5. Prediction horizon
6. Required interpretability

Return JSON with: recommended_model, reasoning, alternative_models, expected_performance."""

# ---------------------------------------------------------------------------
# Prediction chat
# ---------------------------------------------------------------------------

PREDICTION_CHAT_PROMPT = """\
You are a predictive analytics expert answering questions about predictions.

PREDICTION:
Target: {target}
Model: {model_type}
Trend: {trend}
Confidence: {confidence}
Horizon: {horizon}

FORECAST:
{forecast_summary}

EXPLAINABILITY:
{explainability}

QUESTION: {question}

TASK:
Answer the question using the prediction data and analysis.
Provide a clear, business-friendly answer with supporting evidence."""

# ---------------------------------------------------------------------------
# Risk assessment
# ---------------------------------------------------------------------------

RISK_ASSESSMENT_PROMPT = """\
Assess the risks associated with the following forecast.

FORECAST:
{forecast_summary}

TREND: {trend}
VOLATILITY: {volatility}
CONFIDENCE: {confidence}

TASK:
Assess risks on a scale of 1-100:
1. Downside risk (what could go wrong)
2. Upside opportunity (what could go better)
3. Model risk (reliability concerns)
4. Data risk (data quality concerns)
5. External risk (market/competition factors)

Return JSON with: risk_score, risk_factors (each with factor, score, explanation), overall_assessment."""
