"""Load dashboard data for report generation."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Engine, text


class DataService:
    """Loads and prepares data from dashboards for report generation."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def load_dashboard_data(self, dashboard_id: str) -> dict[str, Any]:
        """Load dashboard and execute all widget queries."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text("SELECT id, name, description, widgets FROM dashboards WHERE id = :id"),
                {"id": dashboard_id},
            )
            row = result.fetchone()
            if row is None:
                raise ValueError(f"Dashboard {dashboard_id} not found")

            dashboard: dict[str, Any] = {
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "widgets": row[3] if isinstance(row[3], list) else json.loads(row[3] or "[]"),
            }

            datasets: dict[str, Any] = {}
            for widget in dashboard["widgets"]:
                wid = widget.get("id", "unknown")
                sql_query = widget.get("sql", "")
                if not sql_query:
                    continue
                try:
                    data_result = conn.execute(text(sql_query))
                    columns = list(data_result.keys())
                    rows = [dict(zip(columns, r, strict=False)) for r in data_result.fetchall()]
                    datasets[wid] = {
                        "title": widget.get("title", wid),
                        "chart_type": widget.get("chart", widget.get("type", "table")),
                        "columns": columns,
                        "rows": rows,
                    }
                except Exception:  # noqa: BLE001
                    datasets[wid] = {
                        "title": widget.get("title", wid),
                        "chart_type": widget.get("chart", widget.get("type", "table")),
                        "columns": [],
                        "rows": [],
                        "error": "Query failed",
                    }

            dashboard["datasets"] = datasets
            return dashboard

    def build_data_context(self, dashboard: dict[str, Any]) -> str:
        """Build a text representation of all dashboard data for LLM context."""
        lines: list[str] = []
        name = dashboard.get("name", "Dashboard")
        lines.append(f"DASHBOARD: {name}")
        lines.append(f"DESCRIPTION: {dashboard.get('description', '')}\n")

        for ds_id, ds in dashboard.get("datasets", {}).items():
            title = ds.get("title", ds_id)
            rows = ds.get("rows", [])
            columns = ds.get("columns", [])
            if not rows:
                lines.append(f"TABLE: {title} (empty)")
                continue

            lines.append(f"TABLE: {title}")
            lines.append(f"COLUMNS: {', '.join(str(c) for c in columns)}")
            lines.append(f"ROWS: {len(rows)}")
            for row in rows[:15]:
                vals = [f"{k}={v}" for k, v in row.items()]
                lines.append(f"  {', '.join(vals)}")
            lines.append("")

        return "\n".join(lines)

    def extract_kpis(self, dashboard: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract numeric KPIs from dashboard data."""
        kpis: list[dict[str, Any]] = []
        for ds_id, ds in dashboard.get("datasets", {}).items():
            rows = ds.get("rows", [])
            title = ds.get("title", ds_id)
            if not rows:
                continue

            # Identify numeric columns
            for col in rows[0]:
                values = []
                for r in rows:
                    try:
                        values.append(float(r.get(col, 0)))
                    except (TypeError, ValueError):
                        continue
                if values:
                    total = sum(values)
                    total / len(values)
                    kpis.append(
                        {
                            "name": f"{title} — {col}",
                            "value": round(total, 2),
                            "unit": "",
                            "change_pct": 0.0,
                            "trend": "stable",
                            "description": f"Sum of {col} in {title}",
                        }
                    )
                    if len(kpis) >= 20:
                        return kpis
        return kpis

    def extract_chart_data(self, dashboard: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract chart configurations from dashboard data."""
        charts: list[dict[str, Any]] = []
        for ds_id, ds in dashboard.get("datasets", {}).items():
            chart_type = ds.get("chart_type", "table")
            if chart_type in ("table", "text"):
                continue
            rows = ds.get("rows", [])
            charts.append(
                {
                    "id": ds_id,
                    "title": ds.get("title", ds_id),
                    "chart_type": chart_type,
                    "data": rows[:50],
                    "config": {},
                }
            )
            if len(charts) >= 10:
                break
        return charts
