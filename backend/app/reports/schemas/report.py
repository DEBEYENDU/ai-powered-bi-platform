"""Pydantic schemas for the Reporting Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# --- Sections / builder ---


class ReportSection(BaseModel):
    section_id: str = Field(..., description="Unique section id within the report")
    kind: str = Field(
        ...,
        description="chart, kpi, table, pivot, text, image, toc, summary, insights, recommendations, signature, qr, appendix",
    )
    title: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    conditions: dict[str, Any] = Field(
        default_factory=dict, description="Conditional display rules"
    )
    order: int = 0


class ReportDefinition(BaseModel):
    title: str
    report_type: str = "custom"
    sections: list[ReportSection] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
    filters: dict[str, Any] = Field(default_factory=dict)
    theme: dict[str, Any] = Field(default_factory=dict)


# --- Reports ---


class ReportCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    report_type: str = "custom"
    template_id: UUID | None = None
    dataset_id: UUID | None = None
    dashboard_id: UUID | None = None
    definition: ReportDefinition
    tags: list[str] = Field(default_factory=list)


class ReportOut(BaseModel):
    id: UUID
    title: str
    report_type: str
    status: str
    current_version: int
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ReportGenerateRequest(BaseModel):
    report_id: UUID | None = Field(None, description="Generate from saved report")
    definition: ReportDefinition | None = Field(None, description="Ad-hoc definition")
    formats: list[str] = Field(
        default_factory=lambda: ["pdf"],
        description="pdf, docx, xlsx, csv, json, html, pptx, png, svg, zip",
    )
    include_ai: bool = True
    ai_sections: list[str] = Field(
        default_factory=lambda: ["summary", "insights", "recommendations"]
    )
    variables: dict[str, Any] = Field(default_factory=dict)


class GeneratedArtifact(BaseModel):
    format: str
    storage_path: str
    file_size: int = 0
    checksum_sha256: str = ""


class ReportGenerateResponse(BaseModel):
    report_id: UUID
    version_number: int
    artifacts: list[GeneratedArtifact]
    execution_time_ms: float
    ai_citations: list[dict[str, Any]] = Field(default_factory=list)


# --- Templates ---


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    layout: dict[str, Any] = Field(default_factory=dict)
    sections: list[ReportSection] = Field(default_factory=list)
    shared: bool = False


class TemplateOut(BaseModel):
    id: UUID
    name: str
    current_version: int
    approved: bool
    shared: bool
    updated_at: datetime


class TemplateApprove(BaseModel):
    approved: bool = True
    approved_by: str = ""


# --- Versions ---


class VersionOut(BaseModel):
    version_number: int
    rendered_formats: list[str] = Field(default_factory=list)
    checksum_sha256: str = ""
    approved_by: str = ""
    change_note: str = ""
    created_at: datetime


class VersionCompare(BaseModel):
    from_version: int
    to_version: int
    added_sections: list[str] = Field(default_factory=list)
    removed_sections: list[str] = Field(default_factory=list)
    changed_sections: list[str] = Field(default_factory=list)


# --- Scheduling ---


class ScheduleCreate(BaseModel):
    report_id: UUID
    frequency: str = Field(
        "daily", description="one_time, hourly, daily, weekly, monthly, quarterly, yearly, cron"
    )
    cron_expression: str = ""
    timezone: str = "UTC"
    enabled: bool = True
    max_retries: int = 3
    distribution: dict[str, Any] = Field(default_factory=dict)


class ScheduleOut(BaseModel):
    id: UUID
    report_id: UUID
    frequency: str
    timezone: str
    enabled: bool
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None


# --- Sharing / permissions ---


class ShareCreate(BaseModel):
    granted_to: str = Field(..., description="user id, role, department, or 'org'")
    role: str = Field("viewer", description="owner, editor, reviewer, viewer")
    can_export: bool = True
    can_distribute: bool = False


class ShareOut(BaseModel):
    id: UUID
    granted_to: str
    role: str
    can_export: bool
    can_distribute: bool


# --- Search / history ---


class ReportSearch(BaseModel):
    query: str = ""
    report_type: str | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)
    limit: int = 20
    offset: int = 0


class ReportHistoryEntry(BaseModel):
    action: str
    user_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
