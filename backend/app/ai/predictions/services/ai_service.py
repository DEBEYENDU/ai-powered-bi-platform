"""AI service — wraps the LLM provider for prediction explanations."""

from __future__ import annotations

from typing import Any

from app.ai.predictions.prompts.templates import (
    FORECAST_EXPLANATION_PROMPT,
    PREDICTION_CHAT_PROMPT,
    RECOMMENDATIONS_PROMPT,
    RISK_ASSESSMENT_PROMPT,
    ROOT_CAUSE_PROMPT,
    SYSTEM_PROMPT,
    WHATIF_PROMPT,
)
from app.ai.providers.registry import get_provider


def _get_llm() -> Any:
    return get_provider()


def _extract_text(response: Any) -> str:
    """Extract text content from an LLM response."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        if "content" in response:
            c = response["content"]
            if isinstance(c, str):
                return c
            if isinstance(c, list) and len(c) > 0:
                return c[0].get("text", str(c[0]))
        if "choices" in response and len(response["choices"]) > 0:
            choice = response["choices"][0]
            if "message" in choice:
                return choice["message"].get("content", "")
            return choice.get("text", "")
        return str(response)
    if hasattr(response, "choices") and len(response.choices) > 0:
        return response.choices[0].message.content or ""
    return str(response)


async def explain_forecast(
    target: str,
    horizon: str,
    model_type: str,
    confidence: float,
    trend: str,
    growth_pct: float,
    forecast_summary: str,
    metrics: str,
) -> dict[str, Any]:
    """Get AI explanation for a forecast."""
    prompt = FORECAST_EXPLANATION_PROMPT.format(
        target=target,
        horizon=horizon,
        model_type=model_type,
        confidence=confidence,
        trend=trend,
        growth_pct=growth_pct,
        forecast_summary=forecast_summary,
        metrics=metrics,
    )
    try:
        llm = _get_llm()
        raw = await llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        text = _extract_text(raw)
        return {"explanation": text, "confidence": "high"}
    except Exception as exc:
        return {"explanation": f"Explanation unavailable: {exc}", "confidence": "low"}


async def whatif_analysis(
    current_state: str,
    scenario_description: str,
    variables: str,
    target: str,
    horizon: str,
) -> dict[str, Any]:
    """Perform AI-powered what-if analysis."""
    prompt = WHATIF_PROMPT.format(
        current_state=current_state,
        scenario_description=scenario_description,
        variables=variables,
        target=target,
        horizon=horizon,
    )
    try:
        llm = _get_llm()
        raw = await llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        text = _extract_text(raw)
        import json

        try:
            return json.loads(text) if text.startswith("{") else {"analysis": text}
        except (json.JSONDecodeError, ValueError):
            return {"analysis": text}
    except Exception as exc:
        return {"analysis": f"What-if analysis unavailable: {exc}"}


async def root_cause_analysis(
    prediction_history: str,
    feature_importances: str,
    data_changes: str,
) -> dict[str, Any]:
    """Explain why predictions changed."""
    prompt = ROOT_CAUSE_PROMPT.format(
        prediction_history=prediction_history,
        feature_importances=feature_importances,
        data_changes=data_changes,
    )
    try:
        llm = _get_llm()
        raw = await llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        text = _extract_text(raw)
        import json

        try:
            return json.loads(text) if text.startswith("{") else {"analysis": text}
        except (json.JSONDecodeError, ValueError):
            return {"analysis": text}
    except Exception as exc:
        return {"analysis": f"Root cause analysis unavailable: {exc}"}


async def generate_business_recommendations(
    target: str,
    trend: str,
    growth_pct: float,
    risk_score: float,
    horizon: str,
    forecast_summary: str,
    top_factors: str,
) -> list[dict[str, Any]]:
    """Generate AI-powered business recommendations."""
    prompt = RECOMMENDATIONS_PROMPT.format(
        target=target,
        trend=trend,
        growth_pct=growth_pct,
        risk_score=risk_score,
        horizon=horizon,
        forecast_summary=forecast_summary,
        top_factors=top_factors,
    )
    try:
        llm = _get_llm()
        raw = await llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        text = _extract_text(raw)
        import json

        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else [parsed]
        except (json.JSONDecodeError, ValueError):
            return [{"recommendation": text}]
    except Exception:
        return []


async def prediction_chat(
    target: str,
    model_type: str,
    trend: str,
    confidence: float,
    horizon: str,
    forecast_summary: str,
    explainability: str,
    question: str,
) -> dict[str, Any]:
    """Chat about predictions."""
    prompt = PREDICTION_CHAT_PROMPT.format(
        target=target,
        model_type=model_type,
        trend=trend,
        confidence=confidence,
        horizon=horizon,
        forecast_summary=forecast_summary,
        explainability=explainability,
        question=question,
    )
    try:
        llm = _get_llm()
        raw = await llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        text = _extract_text(raw)
        return {"answer": text, "confidence": "high"}
    except Exception as exc:
        return {"answer": f"Error: {exc}", "confidence": "low"}


async def assess_risk_ai(
    forecast_summary: str,
    trend: str,
    volatility: float,
    confidence: float,
) -> dict[str, Any]:
    """AI-powered risk assessment."""
    prompt = RISK_ASSESSMENT_PROMPT.format(
        forecast_summary=forecast_summary,
        trend=trend,
        volatility=volatility,
        confidence=confidence,
    )
    try:
        llm = _get_llm()
        raw = await llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        text = _extract_text(raw)
        import json

        try:
            return json.loads(text) if text.startswith("{") else {"assessment": text}
        except (json.JSONDecodeError, ValueError):
            return {"assessment": text}
    except Exception as exc:
        return {"assessment": f"Risk assessment unavailable: {exc}"}
