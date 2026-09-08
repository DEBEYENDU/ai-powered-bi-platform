"""Pydantic schemas for dashboards."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class Widget(BaseModel):
    widget_id: str = Field(..., description="Unique widget id within the dashboard")
    kind: str = Field(..., description="kpi, chart, table, text, ai_insights, forecast, gauge")
    title: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    position: dict[str, int] = Field(default_factory=dict)
    order: int = 0


class DashboardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    organization_id: str = ""
    layout: dict[str, Any] = Field(default_factory=dict)
    widgets: list[Widget] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    shared: bool = False


class DashboardUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    layout: dict[str, Any] | None = None
    widgets: list[Widget] | None = None
    filters: dict[str, Any] | None = None
    shared: bool | None = None


class DashboardOut(BaseModel):
    id: UUID
    name: str
    description: str = ""
    organization_id: str = ""
    widget_count: int = 0
    shared: bool = False
    archived: bool = False
    created_at: datetime
    updated_at: datetime


class DashboardDetail(DashboardOut):
    layout: dict[str, Any] = Field(default_factory=dict)
    widgets: list[Widget] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)


class DashboardShare(BaseModel):
    shared: bool = True
