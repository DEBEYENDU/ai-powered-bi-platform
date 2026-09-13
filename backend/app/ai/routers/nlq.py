"""NLQ (Natural Language to SQL) API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.nlq.nl2sql_service import NL2SQLService
from app.ai.schemas.nlq import NLQExplainRequest, NLQQueryRequest
from app.db.session import get_db, get_engine

nlq_router = APIRouter(prefix="/ai", tags=["Natural Language SQL"])


def _get_service(db: Session = Depends(get_db)) -> NL2SQLService:
    return NL2SQLService(engine=get_engine())


@nlq_router.post("/query", response_model=dict)
async def nlq_query(
    request: NLQQueryRequest = Body(...),
    service: NL2SQLService = Depends(_get_service),
):
    """Convert a natural language question to SQL, execute it, and return results."""
    try:
        result = await service.query(
            question=request.question,
            include_chart=request.include_chart,
            temperature=request.temperature,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc


@nlq_router.post("/explain", response_model=dict)
async def nlq_explain(
    request: NLQExplainRequest = Body(...),
    service: NL2SQLService = Depends(_get_service),
):
    """Explain what a SQL query does in plain language."""
    try:
        result = await service.explain_sql(
            sql=request.sql,
            temperature=request.temperature,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Explain failed: {exc}") from exc


@nlq_router.get("/schema", response_model=dict)
async def nlq_schema(
    force_refresh: bool = False,
    service: NL2SQLService = Depends(_get_service),
):
    """Return the full database schema as structured JSON."""
    try:
        schema = service.get_schema(force_refresh=force_refresh)
        return schema
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Schema introspection failed: {exc}") from exc
