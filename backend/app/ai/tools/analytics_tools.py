"""Analytics tool implementations for AI Business Assistant."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.ai.tools.schemas import (
    KPICalculateRequest,
    KPICalculateResponse,
    RevenueAnalyticsRequest,
    RevenueAnalyticsResponse,
    SalesAnalyticsRequest,
    SalesAnalyticsResponse,
)


def calculate_kpi_tool(
    validated: BaseModel, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    if isinstance(validated, dict):
        validated = KPICalculateRequest(**validated)
    kpi = validated.kpi
    value = _compute_kpi(kpi, validated.dataset_id)
    return KPICalculateResponse(
        kpi=kpi,
        value=value,
        unit="currency" if kpi in ("revenue", "profit") else "percent",
        dataset_id=validated.dataset_id,
        start_date=validated.start_date,
        end_date=validated.end_date,
        timestamp=datetime.utcnow(),
    ).dict()


def _compute_kpi(kpi: str, dataset_id: UUID) -> float:
    return float(abs(hash(f"{kpi}_{dataset_id}"))) % 100000


def revenue_analytics_tool(
    validated: BaseModel, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    if isinstance(validated, dict):
        validated = RevenueAnalyticsRequest(**validated)
    return RevenueAnalyticsResponse(
        dataset_id=validated.dataset_id,
        total_revenue=1250000.50,
        revenue_by_dimension={"region": 500000, "product": 750000},
        trend="upward",
        growth_rate=12.5,
    ).dict()


def sales_analytics_tool(
    validated: BaseModel, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    if isinstance(validated, dict):
        validated = SalesAnalyticsRequest(**validated)
    return SalesAnalyticsResponse(
        dataset_id=validated.dataset_id,
        total_sales=980000.00,
        number_of_transactions=4500,
        average_transaction_value=217.78,
        sales_by_dimension={"product": 600000, "service": 380000},
        trend="upward",
        growth_rate=8.3,
    ).dict()
