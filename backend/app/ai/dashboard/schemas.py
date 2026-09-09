"""AI Dashboard Generator schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# --- Widget Types ---
WIDGET_TYPES = [
    "kpi", "line", "bar", "area", "pie", "donut", "scatter",
    "heatmap", "treemap", "gauge", "table", "pivot", "map",
    "timeline", "text", "forecast",
]

CHART_TYPES = [
    "number", "line", "bar", "area", "pie", "donut", "scatter",
    "heatmap", "treemap", "gauge", "table", "pivot", "map",
    "timeline", "text", "forecast",
]

FILTER_TYPES = [
    "date", "region", "country", "department", "category",
    "customer", "employee", "organization", "status", "product", "custom",
]

TEMPLATES = {
    "sales": {"title": "Sales Dashboard", "prompt": "Create a sales dashboard with revenue, deals, pipeline, and conversion metrics"},
    "finance": {"title": "Finance Dashboard", "prompt": "Create a finance dashboard with P&L, cash flow, budget variance, and ROI"},
    "marketing": {"title": "Marketing Dashboard", "prompt": "Create a marketing dashboard with campaign performance, CAC, ROI, and channel metrics"},
    "hr": {"title": "HR Dashboard", "prompt": "Create an HR dashboard with headcount, turnover, hiring pipeline, and satisfaction"},
    "operations": {"title": "Operations Dashboard", "prompt": "Create an operations dashboard with efficiency, downtime, throughput, and quality metrics"},
    "supply_chain": {"title": "Supply Chain Dashboard", "prompt": "Create a supply chain dashboard with inventory, lead times, supplier performance, and logistics"},
    "customer_support": {"title": "Customer Support Dashboard", "prompt": "Create a customer support dashboard with ticket volume, resolution time, CSAT, and agent performance"},
    "manufacturing": {"title": "Manufacturing Dashboard", "prompt": "Create a manufacturing dashboard with OEE, defect rate, throughput, and maintenance"},
    "healthcare": {"title": "Healthcare Dashboard", "prompt": "Create a healthcare dashboard with patient volume, wait times, bed occupancy, and outcomes"},
    "education": {"title": "Education Dashboard", "prompt": "Create an education dashboard with enrollment, grades, attendance, and graduation rates"},
    "retail": {"title": "Retail Dashboard", "prompt": "Create a retail dashboard with sales per store, foot traffic, basket size, and inventory turnover"},
}


# --- Request Schemas ---

class DashboardGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Natural language description of the dashboard")
    template: str | None = Field(None, description="Optional template name to customize")
    organization_id: str | None = None
    save: bool = Field(True, description="Whether to save the dashboard to the database")


class DashboardImproveRequest(BaseModel):
    dashboard_id: str = Field(..., description="Dashboard to improve")
    instruction: str = Field(..., min_length=1, description="How to improve the dashboard")


class DashboardExplainRequest(BaseModel):
    dashboard_id: str | None = None
    widgets: list[dict[str, Any]] | None = None


# --- Response Schemas ---

class WidgetOut(BaseModel):
    id: str
    type: str
    title: str
    sql: str = ""
    explanation: str = ""
    chart: str = "number"
    columns: list[str] = []
    position: dict[str, int] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""


class DashboardGenerateResponse(BaseModel):
    success: bool
    dashboard_id: str | None = None
    title: str
    description: str
    widgets: list[WidgetOut] = []
    layout: dict[str, Any] = Field(default_factory=dict)
    filters: list[dict[str, Any]] = []
    theme: dict[str, Any] = Field(default_factory=dict)
    generation_time_ms: float = 0
    error: str | None = None


class DashboardImproveResponse(BaseModel):
    success: bool
    dashboard_id: str
    title: str
    description: str
    widgets: list[WidgetOut] = []
    layout: dict[str, Any] = Field(default_factory=dict)
    change_summary: str = ""
    error: str | None = None


class DashboardExplainResponse(BaseModel):
    explanations: list[dict[str, Any]] = []


class DashboardVersionOut(BaseModel):
    id: str
    version_number: int
    title: str
    change_summary: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TemplateOut(BaseModel):
    id: str
    title: str
    prompt: str
