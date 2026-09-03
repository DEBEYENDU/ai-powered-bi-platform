"""Versioned API aggregation (/api/v1 + legacy unversioned aliases)."""

from __future__ import annotations

from fastapi import APIRouter

from app.ai.routers.ai_assistant import ai_router
from app.analytics.routers.analytics import router as analytics_router
from app.dataset.routers.dataset import router as dataset_router
from app.etl.routers.etl import router as etl_router
from app.iam.routers.auth import router as auth_router
from app.reports.routers.reports import reports_router

api_router = APIRouter(prefix="/api/v1")
for _router in (auth_router, dataset_router, etl_router,
                analytics_router, ai_router, reports_router):
    api_router.include_router(_router)

# Legacy aliases so existing clients keep working during migration.
legacy_router = APIRouter()
for _router in (auth_router, dataset_router, etl_router,
                analytics_router, ai_router, reports_router):
    legacy_router.include_router(_router)
