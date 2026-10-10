"""NLQ (Natural Language to SQL) API router."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.nlq.nl2sql_service import NL2SQLService
from app.ai.schemas.nlq import NLQExplainRequest, NLQQueryRequest
from app.db.session import get_db, get_engine
from app.dependencies.deps import get_current_user, require_organization

nlq_router = APIRouter(prefix="/ai", tags=["Natural Language SQL"])


def _get_service(
    db: Session = Depends(get_db),
    organization_id: str = Depends(require_organization),
) -> NL2SQLService:
    return NL2SQLService(engine=get_engine(), organization_id=organization_id)


@nlq_router.post("/query", response_model=dict)
async def nlq_query(
    request: NLQQueryRequest = Body(...),
    service: NL2SQLService = Depends(_get_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
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
        raise HTTPException(status_code=500, detail="Unable to process the NLQ request.") from exc


@nlq_router.post("/explain", response_model=dict)
async def nlq_explain(
    request: NLQExplainRequest = Body(...),
    service: NL2SQLService = Depends(_get_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Explain what a SQL query does in plain language."""
    try:
        result = await service.explain_sql(
            sql=request.sql,
            temperature=request.temperature,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to process the explain request.") from exc


@nlq_router.get("/schema", response_model=dict)
async def nlq_schema(
    force_refresh: bool = False,
    service: NL2SQLService = Depends(_get_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Return the full database schema as structured JSON."""
    try:
        schema = service.get_schema(force_refresh=force_refresh)
        return schema
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to retrieve schema.") from exc
