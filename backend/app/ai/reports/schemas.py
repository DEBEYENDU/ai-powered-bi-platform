"""Request / response schemas for the AI Report Generator."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReportType(str, Enum):
    EXECUTIVE = "executive"
    SALES = "sales"
    MARKETING = "marketing"
    FINANCE = "finance"
    OPERATIONS = "operations"
    CUSTOMER = "customer"
    INVENTORY = "inventory"
    HR = "hr"
    MANUFACTURING = "manufacturing"
    HEALTHCARE = "healthcare"
    RETAIL = "retail"
    CUSTOM = "custom"


class ExportFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    CSV = "csv"
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"


class ScheduleFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CRON = "cron"


class ReportStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    SCHEDULED = "scheduled"


# --- Request ---


class GenerateReportRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Natural language report description")
    dashboard_id: str | None = Field(None, description="Dashboard to pull data from")
    report_type: ReportType = Field(ReportType.CUSTOM)
    formats: list[ExportFormat] = Field(default_factory=lambda: [ExportFormat.PDF])
    sections: list[str] | None = Field(
        None,
        description="Specific sections to include. None = auto-detect from prompt.",
    )
    branding: dict[str, Any] = Field(
        default_factory=dict,
        description="Logo, colors, font, header, footer, watermark",
    )
    schedule: dict[str, Any] | None = Field(
        None,
        description="Scheduling config: frequency, cron, timezone, recipients",
    )
    organization_id: str | None = None


class ReportFollowUpRequest(BaseModel):
    report_id: str = Field(..., description="Report to ask about")
    question: str = Field(..., min_length=1)


class ReportVersionRollbackRequest(BaseModel):
    version: int = Field(..., ge=1)


class ReportShareRequest(BaseModel):
    recipients: list[str] = Field(..., min_length=1)
    permissions: str = Field("view", description="view, edit, admin")
    expires_in_days: int | None = None


class ReportScheduleRequest(BaseModel):
    frequency: ScheduleFrequency
    cron_expression: str = ""
    timezone: str = "UTC"
    recipients: list[str] = Field(default_factory=list)
    formats: list[ExportFormat] = Field(default_factory=lambda: [ExportFormat.PDF])
    enabled: bool = True


# --- Nested data ---


class ReportSection(BaseModel):
    id: str = ""
    title: str
    content: str = ""
    section_type: str = "text"
    data: dict[str, Any] = Field(default_factory=dict)
    order: int = 0


class ReportKPI(BaseModel):
    name: str
    value: float | str
    unit: str = ""
    change_pct: float = 0.0
    trend: str = "stable"
    target: float | None = None
    description: str = ""


class ReportChart(BaseModel):
    id: str = ""
    title: str
    chart_type: str = "line"
    data: list[dict[str, Any]] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class ReportRecommendation(BaseModel):
    title: str
    description: str
    priority: str = "medium"
    category: str = ""
    expected_impact: str = ""
    confidence: str = "medium"


class ReportRisk(BaseModel):
    title: str
    description: str
    severity: str = "medium"
    likelihood: str = "medium"
    mitigation: str = ""


class ReportInsight(BaseModel):
    title: str
    description: str
    insight_type: str = ""
    metric: str = ""
    change_pct: float = 0.0
    confidence: str = "medium"


class DownloadUrl(BaseModel):
    format: str
    url: str
    file_size: int = 0


class VersionInfo(BaseModel):
    version: int
    created_at: str
    sections_count: int = 0
    formats: list[str] = Field(default_factory=list)


# --- Response ---


class GenerateReportResponse(BaseModel):
    success: bool
    report_id: str | None = None
    title: str = ""
    status: ReportStatus = ReportStatus.PENDING
    report_type: ReportType = ReportType.CUSTOM
    sections: list[ReportSection] = Field(default_factory=list)
    kpis: list[ReportKPI] = Field(default_factory=list)
    charts: list[ReportChart] = Field(default_factory=list)
    insights: list[ReportInsight] = Field(default_factory=list)
    risks: list[ReportRisk] = Field(default_factory=list)
    recommendations: list[ReportRecommendation] = Field(default_factory=list)
    executive_summary: str = ""
    download_urls: list[DownloadUrl] = Field(default_factory=list)
    versions: list[VersionInfo] = Field(default_factory=list)
    generation_time_ms: float = 0.0
    error: str | None = None


class ReportListResponse(BaseModel):
    reports: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class ReportDetailResponse(BaseModel):
    id: str
    title: str
    description: str
    report_type: str
    status: str
    prompt: str = ""
    dashboard_id: str | None = None
    sections: list[ReportSection] = Field(default_factory=list)
    kpis: list[ReportKPI] = Field(default_factory=list)
    charts: list[ReportChart] = Field(default_factory=list)
    insights: list[ReportInsight] = Field(default_factory=list)
    risks: list[ReportRisk] = Field(default_factory=list)
    recommendations: list[ReportRecommendation] = Field(default_factory=list)
    executive_summary: str = ""
    download_urls: list[DownloadUrl] = Field(default_factory=list)
    versions: list[VersionInfo] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: str = ""
    generation_time_ms: float = 0.0


class FollowUpResponse(BaseModel):
    answer: str
    confidence: str = "medium"
    evidence: list[str] = Field(default_factory=list)


class TemplateListItem(BaseModel):
    id: str
    name: str
    description: str
    report_type: str
    sections: list[str] = Field(default_factory=list)
