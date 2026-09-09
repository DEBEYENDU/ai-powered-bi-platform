"""Dashboard validator - validates widgets, SQL, and chart compatibility."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.ai.nlq.sql_validator import SQLValidationError, SQLValidator

VALID_WIDGET_TYPES = {
    "kpi", "line", "bar", "area", "pie", "donut", "scatter",
    "heatmap", "treemap", "gauge", "table", "pivot", "map",
    "timeline", "text", "forecast",
}

CHART_WIDGET_COMPAT: dict[str, set[str]] = {
    "kpi": {"number"},
    "line": {"line", "area"},
    "bar": {"bar"},
    "area": {"area", "line"},
    "pie": {"pie", "donut"},
    "donut": {"donut", "pie"},
    "scatter": {"scatter"},
    "heatmap": {"heatmap"},
    "treemap": {"treemap"},
    "gauge": {"gauge"},
    "table": {"table", "pivot"},
    "pivot": {"pivot", "table"},
    "map": {"map"},
    "timeline": {"timeline", "line"},
    "text": {"text"},
    "forecast": {"line", "area"},
}


class DashboardValidationError(Exception):
    """Raised when dashboard validation fails."""

    def __init__(self, message: str, widget_id: str = "", code: str = "VALIDATION_ERROR") -> None:
        super().__init__(message)
        self.widget_id = widget_id
        self.code = code


class DashboardValidator:
    """Validates dashboard widgets and SQL."""

    def __init__(self, engine: Engine | None = None) -> None:
        self.engine = engine
        self.sql_validator = SQLValidator(allow_writes=False)

    def validate_dashboard(self, dashboard: dict[str, Any]) -> list[dict[str, Any]]:
        """Validate entire dashboard, return list of issues (empty = valid)."""
        issues: list[dict[str, Any]] = []

        widgets = dashboard.get("widgets", [])
        if not widgets:
            issues.append({"severity": "warning", "message": "Dashboard has no widgets"})
            return issues

        seen_ids: set[str] = set()
        for widget in widgets:
            wid = widget.get("id", "")
            if not wid:
                issues.append({"severity": "error", "message": "Widget missing id"})
                continue
            if wid in seen_ids:
                issues.append({"severity": "error", "message": f"Duplicate widget id: {wid}", "widget_id": wid})
            seen_ids.add(wid)

            widget_issues = self.validate_widget(widget)
            issues.extend(widget_issues)

        return issues

    def validate_widget(self, widget: dict[str, Any]) -> list[dict[str, Any]]:
        """Validate a single widget."""
        issues: list[dict[str, Any]] = []
        wid = widget.get("id", "")

        w_type = widget.get("type", "")
        if w_type not in VALID_WIDGET_TYPES:
            issues.append({
                "severity": "error",
                "message": f"Invalid widget type: {w_type}",
                "widget_id": wid,
            })

        chart = widget.get("chart", "number")
        compatible = CHART_WIDGET_COMPAT.get(w_type, set())
        if compatible and chart not in compatible:
            issues.append({
                "severity": "warning",
                "message": f"Chart '{chart}' may not be optimal for widget type '{w_type}'",
                "widget_id": wid,
            })

        sql = widget.get("sql", "")
        if sql and w_type != "text":
            try:
                self.sql_validator.validate(sql)
            except SQLValidationError as exc:
                issues.append({
                    "severity": "error",
                    "message": f"SQL validation failed: {exc}",
                    "widget_id": wid,
                    "code": exc.code,
                })

        return issues

    def validate_sql_execution(self, sql: str) -> dict[str, Any]:
        """Test-execute SQL to verify it runs against the database."""
        if not self.engine:
            return {"success": False, "error": "No database engine configured"}

        try:
            cleaned = self.sql_validator.validate(sql)
        except SQLValidationError as exc:
            return {"success": False, "error": str(exc)}

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(cleaned))
                if result.returns_rows:
                    columns = list(result.keys())
                    row = result.fetchone()
                    return {"success": True, "columns": columns, "sample_row": dict(row) if row else {}}
                return {"success": True, "columns": [], "sample_row": {}}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}
