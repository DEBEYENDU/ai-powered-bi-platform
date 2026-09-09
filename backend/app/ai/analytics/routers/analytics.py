"""AI Business Analyst router — /ai/analyze endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.analytics.schemas import AnalyzeRequest, FollowUpRequest
from app.ai.analytics.service import BusinessAnalystService
from app.db.session import get_db, get_engine

business_analyst_router = APIRouter(prefix="/ai/analyze", tags=["AI Business Analyst"])


def _get_service(
    db: Session = Depends(get_db),
) -> BusinessAnalystService:
    return BusinessAnalystService(engine=get_engine(), db=db)


@business_analyst_router.post("", response_model=dict[str, Any])
async def analyze_dashboard(
    request: AnalyzeRequest = Body(...),
    service: BusinessAnalystService = Depends(_get_service),
):
    """Analyse a dashboard and generate comprehensive business insights.

    Produces: summary, insights, anomalies, root causes, recommendations,
    forecast, chart explanations, risk/opportunity scores.
    """
    try:
        result = await service.analyze(
            dashboard_id=request.dashboard_id,
            summary_type=request.summary_type,
            comparison=request.comparison,
            forecast_days=request.forecast_days,
            include_recommendations=request.include_recommendations,
            include_anomalies=request.include_anomalies,
            include_forecast=request.include_forecast,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


@business_analyst_router.post("/followup", response_model=dict[str, Any])
async def followup_question(
    request: FollowUpRequest = Body(...),
    service: BusinessAnalystService = Depends(_get_service),
):
    """Ask a follow-up question about a dashboard analysis."""
    try:
        result = await service.followup(request)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Follow-up failed: {exc}") from exc
