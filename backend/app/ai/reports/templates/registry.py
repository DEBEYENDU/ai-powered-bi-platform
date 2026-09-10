"""Report type templates — defines default sections for each report type."""

from __future__ import annotations

from typing import Any

REPORT_TEMPLATES: dict[str, dict[str, Any]] = {
    "executive": {
        "name": "Executive Report",
        "description": "High-level strategic overview for board and C-suite",
        "sections": [
            "executive_summary",
            "key_metrics",
            "financial_highlights",
            "strategic_initiatives",
            "risks_and_opportunities",
            "forecast",
            "recommendations",
            "action_items",
        ],
    },
    "sales": {
        "name": "Sales Report",
        "description": "Sales performance, pipeline, and conversion analysis",
        "sections": [
            "executive_summary",
            "revenue_overview",
            "pipeline_analysis",
            "conversion_rates",
            "regional_performance",
            "top_performers",
            "forecast",
            "recommendations",
        ],
    },
    "marketing": {
        "name": "Marketing Report",
        "description": "Campaign performance, ROI, and channel analysis",
        "sections": [
            "executive_summary",
            "campaign_performance",
            "channel_analysis",
            "customer_acquisition",
            "brand_metrics",
            "roi_analysis",
            "recommendations",
        ],
    },
    "finance": {
        "name": "Finance Report",
        "description": "P&L, cash flow, budget variance, and financial health",
        "sections": [
            "executive_summary",
            "income_statement",
            "cash_flow",
            "budget_variance",
            "balance_sheet",
            "financial_ratios",
            "forecast",
            "risks",
        ],
    },
    "operations": {
        "name": "Operations Report",
        "description": "Efficiency, throughput, quality, and process metrics",
        "sections": [
            "executive_summary",
            "efficiency_metrics",
            "throughput_analysis",
            "quality_metrics",
            "bottlenecks",
            "improvements",
            "recommendations",
        ],
    },
    "customer": {
        "name": "Customer Report",
        "description": "Customer segments, retention, churn, and satisfaction",
        "sections": [
            "executive_summary",
            "customer_overview",
            "segmentation",
            "retention_analysis",
            "churn_analysis",
            "lifetime_value",
            "satisfaction_scores",
            "recommendations",
        ],
    },
    "inventory": {
        "name": "Inventory Report",
        "description": "Stock levels, turnover, and supply chain metrics",
        "sections": [
            "executive_summary",
            "inventory_overview",
            "turnover_analysis",
            "stock_alerts",
            "supplier_performance",
            "forecast",
            "recommendations",
        ],
    },
    "hr": {
        "name": "HR Report",
        "description": "Headcount, turnover, hiring, and employee metrics",
        "sections": [
            "executive_summary",
            "headcount_analysis",
            "turnover_metrics",
            "hiring_pipeline",
            "employee_satisfaction",
            "training_and_development",
            "recommendations",
        ],
    },
    "manufacturing": {
        "name": "Manufacturing Report",
        "description": "OEE, defect rates, throughput, and maintenance",
        "sections": [
            "executive_summary",
            "oee_analysis",
            "defect_rates",
            "throughput_metrics",
            "maintenance_schedule",
            "cost_analysis",
            "recommendations",
        ],
    },
    "healthcare": {
        "name": "Healthcare Report",
        "description": "Patient volume, wait times, outcomes, and compliance",
        "sections": [
            "executive_summary",
            "patient_volume",
            "wait_times",
            "outcomes_analysis",
            "bed_occupancy",
            "compliance_metrics",
            "recommendations",
        ],
    },
    "retail": {
        "name": "Retail Report",
        "description": "Sales per store, foot traffic, basket size, and inventory",
        "sections": [
            "executive_summary",
            "store_performance",
            "foot_traffic",
            "basket_analysis",
            "inventory_turnover",
            "promotion_effectiveness",
            "recommendations",
        ],
    },
    "custom": {
        "name": "Custom Report",
        "description": "AI-generated report based on user prompt",
        "sections": [
            "executive_summary",
            "data_analysis",
            "key_findings",
            "risks",
            "recommendations",
        ],
    },
}


def get_template(report_type: str) -> dict[str, Any]:
    """Get template for a report type, falling back to custom."""
    return REPORT_TEMPLATES.get(report_type, REPORT_TEMPLATES["custom"])


def list_templates() -> list[dict[str, Any]]:
    """List all available report templates."""
    return [
        {"id": key, "name": val["name"], "description": val["description"], "sections": val["sections"]}
        for key, val in REPORT_TEMPLATES.items()
    ]
