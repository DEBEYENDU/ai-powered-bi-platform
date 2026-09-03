"""Prompt management system for AI Business Assistant."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class PromptVersion(BaseModel):
    version_id: str = Field(default_factory=lambda: str(uuid4()))
    prompt_id: str = Field(..., description="Unique prompt identifier")
    version_number: int = Field(..., description="Version number")
    template: str = Field(..., description="Prompt template string")
    variables: List[str] = Field(default_factory=list, description="Template variables")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved: bool = False
    approved_by: Optional[str] = Field(None)
    approved_at: Optional[datetime] = Field(None)
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.approved


class PromptTemplate(BaseModel):
    prompt_id: str = Field(..., description="Unique prompt identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(default="", description="Description")
    current_version: int = Field(default=1)
    versions: List[PromptVersion] = Field(default_factory=list)
    category: str = Field(default="general", description="Prompt category")
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def get_active_version(self) -> Optional[PromptVersion]:
        for v in reversed(self.versions):
            if v.approved:
                return v
        if self.versions:
            return self.versions[-1]
        return None


class PromptManager:
    """Manages prompt templates with versioning."""

    def __init__(self) -> None:
        self._templates: Dict[str, PromptTemplate] = {}
        self._default_prompts: Dict[str, str] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        self._default_prompts = {
            "executive_summary": (
                "You are an executive assistant for a BI platform. "
                "Summarize the following business data for executives:\n\n"
                "Data: {data}\n"
                "Time Range: {time_range}\n"
                "Focus Areas: {focus_areas}\n\n"
                "Provide a concise executive summary with key insights, "
                "trends, and recommended actions. Include confidence scores."
            ),
            "root_cause_analysis": (
                "You are a root cause analyst. Analyze the following business issue:\n\n"
                "Issue: {issue}\n"
                "Evidence: {evidence}\n"
                "Time Range: {time_range}\n\n"
                "Provide evidence-based root cause findings with confidence scores. "
                "Never fabricate conclusions."
            ),
            "sales_insights": (
                "You are a sales analytics expert. Provide insights based on:\n\n"
                "Sales Data: {sales_data}\n"
                "Dimensions: {dimensions}\n\n"
                "Analyze trends, patterns, and provide actionable insights."
            ),
            "inventory_insights": (
                "You are an inventory analytics expert. Provide insights based on:\n\n"
                "Inventory Data: {inventory_data}\n\n"
                "Identify anomalies, optimization opportunities, and recommendations."
            ),
            "customer_insights": (
                "You are a customer analytics expert. Analyze customer data:\n\n"
                "Customer Data: {customer_data}\n\n"
                "Provide insights on segmentation, churn risks, and opportunities."
            ),
            "forecast_explanation": (
                "You are a forecasting expert. Explain the forecast:\n\n"
                "Forecast: {forecast}\n"
                "Model Type: {model_type}\n"
                "Confidence Intervals: {confidence_intervals}\n\n"
                "Provide a clear explanation of the forecast, assumptions, and limitations."
            ),
            "dashboard_summary": (
                "You are a dashboard analyst. Summarize this dashboard:\n\n"
                "Dashboard: {dashboard_data}\n"
                "KPIs: {kpis}\n\n"
                "Provide an AI-generated summary with key insights and trends."
            ),
            "report_summary": (
                "You are a report generator. Create an AI-enhanced report:\n\n"
                "Data: {data}\n"
                "Report Type: {report_type}\n"
                "Include recommendations and citations."
            ),
            "recommendation_generation": (
                "You are a business recommendation engine. Generate recommendations:\n\n"
                "Context: {context}\n"
                "Category: {category}\n"
                "Data: {data}\n\n"
                "Provide prioritized, actionable recommendations with expected impact."
            ),
            "general_chat": (
                "You are an AI business assistant for a BI platform. "
                "Answer questions about business data, analytics, KPIs, and dashboards.\n\n"
                "Context: {context}\n\n"
                "If you don't have sufficient data, be explicit about uncertainty."
            ),
        }

    def get_prompt(
        self, prompt_id: str, **variables: Any
    ) -> str:
        if prompt_id in self._default_prompts:
            template = self._default_prompts[prompt_id]
        else:
            template_obj = self._templates.get(prompt_id)
            if template_obj is None:
                raise ValueError(f"Prompt '{prompt_id}' not found")
            active = template_obj.get_active_version()
            if active is None:
                raise ValueError(f"No approved version for prompt '{prompt_id}'")
            template = active.template
        return template.format(**variables)

    def register_template(
        self,
        prompt_id: str,
        name: str,
        template: str,
        variables: List[str],
        category: str = "general",
        tags: Optional[List[str]] = None,
    ) -> PromptTemplate:
        if prompt_id in self._templates:
            template_obj = self._templates[prompt_id]
            version_num = template_obj.current_version + 1
        else:
            version_num = 1
            template_obj = PromptTemplate(
                prompt_id=prompt_id, name=name,
            )
        version = PromptVersion(
            prompt_id=prompt_id,
            version_number=version_num,
            template=template,
            variables=variables,
        )
        template_obj.versions.append(version)
        template_obj.current_version = version_num
        template_obj.name = name
        template_obj.category = category
        template_obj.tags = tags or []
        template_obj.updated_at = datetime.utcnow()
        self._templates[prompt_id] = template_obj
        return template_obj

    def approve_version(self, prompt_id: str, version_number: int, approved_by: str) -> bool:
        template = self._templates.get(prompt_id)
        if template is None:
            return False
        for v in template.versions:
            if v.version_number == version_number:
                v.approved = True
                v.approved_by = approved_by
                v.approved_at = datetime.utcnow()
                return True
        return False

    def get_template(self, prompt_id: str) -> Optional[PromptTemplate]:
        return self._templates.get(prompt_id)

    def list_templates(self) -> List[PromptTemplate]:
        return list(self._templates.values())

    def get_default_prompt_ids(self) -> List[str]:
        return list(self._default_prompts.keys())
