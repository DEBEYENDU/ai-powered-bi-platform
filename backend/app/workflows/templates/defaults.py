"""Predefined workflow templates."""

from __future__ import annotations

from typing import Any

WORKFLOW_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "Weekly Sales Report",
        "description": "Every Monday at 9 AM, analyze sales data and generate an executive report",
        "category": "reporting",
        "trigger_config": {
            "type": "weekly",
            "day_of_week": "monday",
            "time": "09:00",
        },
        "steps": [
            {
                "name": "Analyze Sales",
                "action_type": "analyze_dataset",
                "config": {"analysis_type": "sales"},
                "depends_on": [],
            },
            {
                "name": "Generate Report",
                "action_type": "generate_report",
                "config": {"report_type": "executive", "format": "pdf"},
                "depends_on": ["step_1"],
            },
            {
                "name": "Export PDF",
                "action_type": "export_pdf",
                "config": {"filename": "weekly_sales_report.pdf"},
                "depends_on": ["step_2"],
            },
            {
                "name": "Notify Team",
                "action_type": "send_notification",
                "config": {"message": "Weekly sales report is ready", "kind": "info"},
                "depends_on": ["step_3"],
            },
        ],
        "conditions": [],
        "tags": ["sales", "reporting", "weekly"],
    },
    {
        "name": "Monthly Executive Report",
        "description": "Generate a comprehensive monthly executive report with KPIs and forecasts",
        "category": "reporting",
        "trigger_config": {
            "type": "monthly",
            "day_of_month": 1,
            "time": "09:00",
        },
        "steps": [
            {
                "name": "Analyze KPIs",
                "action_type": "analyze_dataset",
                "config": {"analysis_type": "kpi"},
                "depends_on": [],
            },
            {
                "name": "Generate Forecast",
                "action_type": "generate_forecast",
                "config": {"horizon": "90_days"},
                "depends_on": ["step_1"],
            },
            {
                "name": "Generate Report",
                "action_type": "generate_report",
                "config": {"report_type": "executive", "format": "pdf"},
                "depends_on": ["step_1", "step_2"],
            },
            {
                "name": "Export PDF",
                "action_type": "export_pdf",
                "config": {"filename": "monthly_executive_report.pdf"},
                "depends_on": ["step_3"],
            },
            {
                "name": "Notify Management",
                "action_type": "send_notification",
                "config": {"message": "Monthly executive report is ready", "kind": "info"},
                "depends_on": ["step_4"],
            },
        ],
        "conditions": [],
        "tags": ["executive", "monthly", "kpi"],
    },
    {
        "name": "Daily KPI Monitoring",
        "description": "Monitor key performance indicators daily and alert on anomalies",
        "category": "monitoring",
        "trigger_config": {
            "type": "daily",
            "time": "08:00",
        },
        "steps": [
            {
                "name": "Check KPIs",
                "action_type": "analyze_dataset",
                "config": {"analysis_type": "kpi"},
                "depends_on": [],
            },
            {
                "name": "Detect Anomalies",
                "action_type": "run_ai_agent",
                "config": {
                    "agent_type": "business_analyst",
                    "task": "Check for anomalies in today's KPIs",
                },
                "depends_on": ["step_1"],
            },
            {
                "name": "Alert if Needed",
                "action_type": "create_alert",
                "config": {"severity": "warning", "title": "KPI Anomaly Detected"},
                "depends_on": ["step_2"],
            },
        ],
        "conditions": [
            {"metric": "anomaly_detected", "operator": "eq", "value": True, "step_id": "step_2"}
        ],
        "tags": ["kpi", "daily", "monitoring"],
    },
    {
        "name": "Revenue Alert",
        "description": "Alert when revenue drops below threshold",
        "category": "alerting",
        "trigger_config": {"type": "manual"},
        "steps": [
            {
                "name": "Check Revenue",
                "action_type": "run_sql",
                "config": {
                    "query": "SELECT SUM(amount) as revenue FROM sales WHERE date >= CURRENT_DATE - INTERVAL '1 day'"
                },
                "depends_on": [],
            },
            {
                "name": "Send Alert",
                "action_type": "send_notification",
                "config": {"message": "Revenue has dropped below threshold", "kind": "warning"},
                "depends_on": ["step_1"],
            },
        ],
        "conditions": [{"metric": "revenue", "operator": "lt", "value": 100000}],
        "tags": ["revenue", "alerting"],
    },
    {
        "name": "Inventory Alert",
        "description": "Monitor inventory levels and alert when stock is low",
        "category": "alerting",
        "trigger_config": {"type": "daily", "time": "07:00"},
        "steps": [
            {
                "name": "Check Inventory",
                "action_type": "run_sql",
                "config": {
                    "query": "SELECT product_name, stock_level FROM inventory WHERE stock_level < 10"
                },
                "depends_on": [],
            },
            {
                "name": "Alert Low Stock",
                "action_type": "create_alert",
                "config": {"severity": "critical", "title": "Low Inventory Alert"},
                "depends_on": ["step_1"],
            },
        ],
        "conditions": [],
        "tags": ["inventory", "alerting"],
    },
    {
        "name": "Customer Churn Alert",
        "description": "Monitor customer churn rate and alert if it exceeds threshold",
        "category": "monitoring",
        "trigger_config": {"type": "weekly", "day_of_week": "friday", "time": "09:00"},
        "steps": [
            {
                "name": "Analyze Churn",
                "action_type": "analyze_dataset",
                "config": {"analysis_type": "churn"},
                "depends_on": [],
            },
            {
                "name": "Check Threshold",
                "action_type": "evaluate_condition",
                "config": {"condition": {"metric": "churn_rate", "operator": "gt", "value": 0.08}},
                "depends_on": ["step_1"],
            },
            {
                "name": "Alert Management",
                "action_type": "send_notification",
                "config": {
                    "message": "Customer churn rate exceeds 8% threshold",
                    "kind": "warning",
                },
                "depends_on": ["step_2"],
            },
        ],
        "conditions": [
            {"metric": "churn_rate", "operator": "gt", "value": 0.08, "step_id": "step_1"}
        ],
        "tags": ["churn", "customer", "weekly"],
    },
    {
        "name": "Marketing Performance",
        "description": "Weekly marketing campaign performance analysis and report",
        "category": "reporting",
        "trigger_config": {"type": "weekly", "day_of_week": "friday", "time": "10:00"},
        "steps": [
            {
                "name": "Analyze Campaigns",
                "action_type": "analyze_dataset",
                "config": {"analysis_type": "marketing"},
                "depends_on": [],
            },
            {
                "name": "Generate Report",
                "action_type": "generate_report",
                "config": {"report_type": "marketing", "format": "pdf"},
                "depends_on": ["step_1"],
            },
            {
                "name": "Notify Marketing",
                "action_type": "send_notification",
                "config": {"message": "Marketing performance report is ready", "kind": "info"},
                "depends_on": ["step_2"],
            },
        ],
        "conditions": [],
        "tags": ["marketing", "weekly"],
    },
    {
        "name": "Financial Summary",
        "description": "Monthly financial summary with revenue, expenses, and profit margins",
        "category": "reporting",
        "trigger_config": {"type": "monthly", "day_of_month": 5},
        "steps": [
            {
                "name": "Query Financials",
                "action_type": "run_sql",
                "config": {
                    "query": "SELECT * FROM financial_summary WHERE month = EXTRACT(MONTH FROM CURRENT_DATE)"
                },
                "depends_on": [],
            },
            {
                "name": "Generate Report",
                "action_type": "generate_report",
                "config": {"report_type": "financial", "format": "pdf"},
                "depends_on": ["step_1"],
            },
            {
                "name": "Export to Excel",
                "action_type": "export_excel",
                "config": {"filename": "financial_summary.xlsx"},
                "depends_on": ["step_1"],
            },
            {
                "name": "Notify Finance",
                "action_type": "send_notification",
                "config": {"message": "Monthly financial summary is ready", "kind": "info"},
                "depends_on": ["step_2", "step_3"],
            },
        ],
        "conditions": [],
        "tags": ["finance", "monthly"],
    },
    {
        "name": "Data Quality Monitoring",
        "description": "Monitor data quality across datasets and alert on degradation",
        "category": "monitoring",
        "trigger_config": {"type": "daily", "time": "06:00"},
        "steps": [
            {
                "name": "Check Quality",
                "action_type": "run_ai_agent",
                "config": {
                    "agent_type": "data_quality",
                    "task": "Assess data quality across all datasets",
                },
                "depends_on": [],
            },
            {
                "name": "Evaluate Score",
                "action_type": "evaluate_condition",
                "config": {"condition": {"metric": "quality_score", "operator": "lt", "value": 80}},
                "depends_on": ["step_1"],
            },
            {
                "name": "Alert Data Team",
                "action_type": "send_notification",
                "config": {"message": "Data quality has dropped below 80%", "kind": "warning"},
                "depends_on": ["step_2"],
            },
        ],
        "conditions": [
            {"metric": "quality_score", "operator": "lt", "value": 80, "step_id": "step_1"}
        ],
        "tags": ["data_quality", "daily"],
    },
    {
        "name": "Forecast Monitoring",
        "description": "Monitor forecasts and alert on risk indicators",
        "category": "monitoring",
        "trigger_config": {"type": "daily", "time": "09:00"},
        "steps": [
            {
                "name": "Run Forecast",
                "action_type": "generate_forecast",
                "config": {"target": "revenue", "horizon": "30_days"},
                "depends_on": [],
            },
            {
                "name": "Assess Risk",
                "action_type": "run_ai_agent",
                "config": {"agent_type": "forecast", "task": "Assess forecast risk indicators"},
                "depends_on": ["step_1"],
            },
            {
                "name": "Alert if Risky",
                "action_type": "create_alert",
                "config": {"severity": "warning", "title": "Forecast Risk Detected"},
                "depends_on": ["step_2"],
            },
        ],
        "conditions": [
            {"metric": "risk_score", "operator": "gt", "value": 60, "step_id": "step_2"}
        ],
        "tags": ["forecast", "daily", "monitoring"],
    },
]


def get_templates() -> list[dict[str, Any]]:
    """Return all predefined workflow templates."""
    return WORKFLOW_TEMPLATES


def get_template_by_name(name: str) -> dict[str, Any] | None:
    """Get a template by its name."""
    for t in WORKFLOW_TEMPLATES:
        if t["name"].lower() == name.lower():
            return t
    return None
