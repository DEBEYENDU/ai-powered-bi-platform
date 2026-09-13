"""Versioned API aggregation (/api/v1 + legacy unversioned aliases)."""

from __future__ import annotations

from fastapi import APIRouter

from app.admin.routers.admin import admin_router
from app.ai.agents.routers.agents_router import agents_router
from app.ai.analytics.routers.analytics import business_analyst_router
from app.ai.data_engineering.routers.de_router import de_router
from app.ai.predictions.routers.predictions_router import predictions_router
from app.ai.reports.routers.reports import ai_reports_router
from app.ai.routers.ai_assistant import ai_router
from app.ai.routers.dashboard_gen import dashboard_gen_router
from app.ai.routers.nlq import nlq_router
from app.analytics.routers.analytics import router as analytics_router
from app.copilot.routers.copilot import copilot_router
from app.dashboards.router import router as dashboards_router
from app.dataset.routers.dataset import router as dataset_router
from app.etl.routers.etl import router as etl_router
from app.iam.routers.auth import router as auth_router
from app.knowledge.routers.collections import collections_router
from app.knowledge.routers.documents import documents_router
from app.knowledge.routers.rag import rag_router
from app.knowledge.routers.search import search_router
from app.reports.routers.reports import reports_router
from app.workflows.routers.workflow_router import workflow_router

knowledge_router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])
knowledge_router.include_router(documents_router)
knowledge_router.include_router(collections_router)
knowledge_router.include_router(search_router)
knowledge_router.include_router(rag_router)

api_router = APIRouter(prefix="/api/v1")
for _router in (
    auth_router,
    dataset_router,
    etl_router,
    analytics_router,
    ai_router,
    nlq_router,
    dashboard_gen_router,
    business_analyst_router,
    ai_reports_router,
    de_router,
    predictions_router,
    reports_router,
    admin_router,
    dashboards_router,
    agents_router,
    workflow_router,
    knowledge_router,
    copilot_router,
):
    api_router.include_router(_router)

# Legacy aliases so existing clients keep working during migration.
legacy_router = APIRouter()
for _router in (
    auth_router,
    dataset_router,
    etl_router,
    analytics_router,
    ai_router,
    nlq_router,
    dashboard_gen_router,
    business_analyst_router,
    ai_reports_router,
    de_router,
    predictions_router,
    reports_router,
    admin_router,
    dashboards_router,
    agents_router,
    workflow_router,
    knowledge_router,
    copilot_router,
):
    legacy_router.include_router(_router)
