"""AI Business Analyst — main orchestrator service.

Coordinates: statistics → anomaly detection → forecasting → LLM insight
generation → recommendations → summary.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.ai.analytics.anomaly.detector import detect_all_anomalies
from app.ai.analytics.forecasting.engine import generate_forecast
from app.ai.analytics.prompts.templates import (
    ANOMALY_PROMPT,
    CHART_EXPLAIN_PROMPT,
    FOLLOWUP_PROMPT,
    FORECAST_PROMPT,
    INSIGHT_PROMPT,
    ROOT_CAUSE_PROMPT,
    SYSTEM_PROMPT,
)
from app.ai.analytics.recommendations.engine import generate_recommendations
from app.ai.analytics.schemas import (
    Anomaly,
    AnomalyType,
    ChartExplanation,
    Confidence,
    FollowUpRequest,
    Forecast,
    ForecastPoint,
    Insight,
    InsightType,
    RootCause,
)
from app.ai.analytics.statistics.engine import (
    compute_growth_rate,
    compute_volatility,
    detect_trend,
    rank_values,
)
from app.ai.analytics.summaries.generator import generate_summary


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _safe_json_parse(text_content: str) -> Any:
    """Attempt to extract JSON from LLM response, handling markdown fences."""
    cleaned = text_content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON array in the text
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass
        return []


class BusinessAnalystService:
    """Orchestrates all AI Business Analyst capabilities."""

    def __init__(self, engine: Engine, db: Session) -> None:
        self._engine = engine
        self._db = db

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_dashboard_data(self, dashboard_id: str) -> dict[str, Any]:
        """Load dashboard config and execute widget queries to get data."""
        # Load dashboard from database
        result = self._db.execute(
            text("SELECT id, name, description, widgets FROM dashboards WHERE id = :id"),
            {"id": dashboard_id},
        )
        row = result.fetchone()
        if row is None:
            raise ValueError(f"Dashboard {dashboard_id} not found")

        dashboard = {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "widgets": row[3] if isinstance(row[3], list) else json.loads(row[3] or "[]"),
        }

        # Execute each widget's SQL to get data
        datasets: dict[str, Any] = {}
        for widget in dashboard["widgets"]:
            widget_id = widget.get("id", _uid())
            sql_query = widget.get("sql", "")
            if not sql_query:
                continue

            try:
                with self._engine.connect() as conn:
                    data_result = conn.execute(text(sql_query))
                    columns = list(data_result.keys())
                    rows = [dict(zip(columns, row, strict=False)) for row in data_result.fetchall()]
                    datasets[widget_id] = {
                        "title": widget.get("title", widget_id),
                        "chart_type": widget.get("chart", widget.get("type", "table")),
                        "columns": columns,
                        "rows": rows,
                    }
            except Exception:  # noqa: BLE001
                datasets[widget_id] = {
                    "title": widget.get("title", widget_id),
                    "chart_type": widget.get("chart", widget.get("type", "table")),
                    "columns": [],
                    "rows": [],
                    "error": "Query execution failed",
                }

        dashboard["datasets"] = datasets
        return dashboard

    def _extract_numeric_columns(self, rows: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
        """Identify numeric and non-numeric columns from data rows."""
        if not rows:
            return [], []

        numeric_cols: list[str] = []
        date_cols: list[str] = []
        for col in rows[0]:
            values = [r.get(col) for r in rows[:10]]
            numeric_count = 0
            for v in values:
                try:
                    float(v)
                    numeric_count += 1
                except (TypeError, ValueError):
                    pass
            if numeric_count > len(values) * 0.6:
                numeric_cols.append(col)
            elif any(
                kw in col.lower() for kw in ("date", "time", "day", "month", "year", "period")
            ):
                date_cols.append(col)

        return numeric_cols, date_cols

    def _flatten_datasets(
        self, datasets: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], list[str], str | None]:
        """Flatten all widget datasets into a single analytic context."""
        all_rows: list[dict[str, Any]] = []
        all_numeric: list[str] = []
        date_col: str | None = None

        for ds in datasets.values():
            rows = ds.get("rows", [])
            if not rows:
                continue

            numeric_cols, date_cols = self._extract_numeric_columns(rows)
            all_numeric.extend(numeric_cols)
            if date_cols and date_col is None:
                date_col = date_cols[0]

            # Prefix column names with widget title to avoid collisions
            title = ds.get("title", "")
            for row in rows:
                prefixed = {}
                for k, v in row.items():
                    prefixed[f"{title}_{k}" if k in all_numeric else k] = v
                all_rows.append(prefixed)

        # Deduplicate numeric columns
        seen: set[str] = set()
        unique_numeric: list[str] = []
        for c in all_numeric:
            if c not in seen:
                seen.add(c)
                unique_numeric.append(c)

        return all_rows, unique_numeric, date_col

    def _build_data_context(self, datasets: dict[str, Any]) -> str:
        """Build a text representation of all dataset data for LLM context."""
        lines: list[str] = []
        for ds_id, ds in datasets.items():
            title = ds.get("title", ds_id)
            rows = ds.get("rows", [])
            columns = ds.get("columns", [])
            if not rows:
                lines.append(f"TABLE: {title} (empty)")
                continue

            lines.append(f"TABLE: {title}")
            lines.append(f"COLUMNS: {', '.join(columns)}")
            lines.append(f"ROWS: {len(rows)}")

            # Show first 20 rows as sample
            for row in rows[:20]:
                vals = [f"{k}={v}" for k, v in row.items()]
                lines.append(f"  {', '.join(vals)}")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # LLM integration
    # ------------------------------------------------------------------

    def _get_provider(self) -> Any:
        """Get the configured AI provider."""
        from app.ai.providers.registry import get_provider

        return get_provider()

    async def _llm_insights(self, data_context: str, comparison_context: str = "") -> list[Insight]:
        """Generate insights via LLM."""
        try:
            provider = self._get_provider()
            prompt = INSIGHT_PROMPT.format(
                data_context=data_context[:8000],
                comparison_context=comparison_context,
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            response = await provider.chat(messages)
            content = response.get("content", "")
            parsed = _safe_json_parse(content)
            if isinstance(parsed, list):
                return [
                    Insight(
                        id=_uid(),
                        type=InsightType(i.get("type", "positive_trend")),
                        title=i.get("title", "Untitled"),
                        description=i.get("description", ""),
                        evidence=i.get("evidence", []),
                        confidence=Confidence(i.get("confidence", "medium")),
                        metric=i.get("metric", ""),
                        current_value=float(i.get("current_value", 0)),
                        previous_value=i.get("previous_value"),
                        change_pct=float(i.get("change_pct", 0)),
                        impact=i.get("impact", ""),
                    )
                    for i in parsed
                    if i.get("title")
                ]
        except Exception:  # noqa: BLE001, S110
            pass
        return []

    async def _llm_anomalies(self, data_context: str) -> list[Anomaly]:
        """Generate anomaly analysis via LLM."""
        try:
            provider = self._get_provider()
            prompt = ANOMALY_PROMPT.format(data_context=data_context[:8000])
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            response = await provider.chat(messages)
            content = response.get("content", "")
            parsed = _safe_json_parse(content)
            if isinstance(parsed, list):
                return [
                    Anomaly(
                        id=_uid(),
                        type=AnomalyType(a.get("type", "outlier")),
                        title=a.get("title", "Untitled"),
                        description=a.get("description", ""),
                        severity=a.get("severity", "medium"),
                        metric=a.get("metric", ""),
                        expected_value=float(a.get("expected_value", 0)),
                        actual_value=float(a.get("actual_value", 0)),
                        deviation_pct=float(a.get("deviation_pct", 0)),
                        confidence=Confidence(a.get("confidence", "medium")),
                        evidence=a.get("evidence", []),
                    )
                    for a in parsed
                    if a.get("title")
                ]
        except Exception:  # noqa: BLE001, S110
            pass
        return []

    async def _llm_root_causes(
        self,
        current_context: str,
        previous_context: str,
        change_summary: str,
    ) -> list[RootCause]:
        """Generate root cause analysis via LLM."""
        try:
            provider = self._get_provider()
            prompt = ROOT_CAUSE_PROMPT.format(
                current_context=current_context[:4000],
                previous_context=previous_context[:4000],
                change_summary=change_summary,
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            response = await provider.chat(messages)
            content = response.get("content", "")
            parsed = _safe_json_parse(content)
            if isinstance(parsed, list):
                return [
                    RootCause(
                        factor=rc.get("factor", "Unknown"),
                        contribution_pct=float(rc.get("contribution_pct", 0)),
                        explanation=rc.get("explanation", ""),
                        evidence=rc.get("evidence", []),
                    )
                    for rc in parsed
                    if rc.get("factor")
                ]
        except Exception:  # noqa: BLE001, S110
            pass
        return []

    async def _llm_forecast_narrative(self, forecast: Forecast) -> str:
        """Generate a business narrative for the forecast."""
        try:
            provider = self._get_provider()
            points_text = "\n".join(
                f"  {p.date}: {p.value:.2f} [{p.lower_bound:.2f}-{p.upper_bound:.2f}]"
                for p in forecast.points[:10]
            )
            prompt = FORECAST_PROMPT.format(
                metric=forecast.metric,
                horizon_days=forecast.horizon_days,
                trend=forecast.trend,
                seasonality="Yes" if forecast.seasonality_detected else "No",
                forecast_points=points_text,
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            response = await provider.chat(messages)
            return response.get("content", "")
        except Exception:  # noqa: BLE001
            return ""

    async def _llm_chart_explanation(
        self, title: str, chart_type: str, data_summary: str
    ) -> dict[str, str]:
        """Explain a chart using LLM."""
        try:
            provider = self._get_provider()
            prompt = CHART_EXPLAIN_PROMPT.format(
                title=title,
                chart_type=chart_type,
                data_summary=data_summary[:3000],
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            response = await provider.chat(messages)
            content = response.get("content", "")
            parsed = _safe_json_parse(content)
            if isinstance(parsed, dict):
                return parsed
            # If not JSON, use raw text
            return {
                "meaning": content[:500] if content else "",
                "action": "",
                "importance": "medium",
                "confidence": "medium",
            }
        except Exception:  # noqa: BLE001
            return {"meaning": "", "action": "", "importance": "", "confidence": "low"}

    # ------------------------------------------------------------------
    # Statistical insight generation (fallback / supplement)
    # ------------------------------------------------------------------

    def _statistical_insights(
        self,
        datasets: dict[str, Any],
        all_rows: list[dict[str, Any]],
        numeric_cols: list[str],
    ) -> list[Insight]:
        """Generate insights from statistical analysis of the data."""
        insights: list[Insight] = []

        for ds_id, ds in datasets.items():
            rows = ds.get("rows", [])
            title = ds.get("title", ds_id)
            if not rows:
                continue

            ds_numeric, _ = self._extract_numeric_columns(rows)

            for col in ds_numeric:
                values = [r.get(col) for r in rows]

                # Trend analysis
                trend = detect_trend(values)
                if trend["direction"] != "flat" and abs(trend["change_pct"]) > 5:
                    insight_type = (
                        InsightType.POSITIVE_TREND
                        if trend["direction"] == "up"
                        else InsightType.NEGATIVE_TREND
                    )
                    insights.append(
                        Insight(
                            id=_uid(),
                            type=insight_type,
                            title=f"{title} — {col} {'increasing' if trend['direction'] == 'up' else 'decreasing'}",
                            description=(
                                f"{col} shows a {trend['direction']} trend "
                                f"({trend['change_pct']:+.1f}% change, R²={trend['r_squared']:.2f})"
                            ),
                            evidence=[
                                f"Trend direction: {trend['direction']}",
                                f"Change: {trend['change_pct']:.1f}%",
                            ],
                            confidence=Confidence.HIGH
                            if trend["r_squared"] > 0.7
                            else Confidence.MEDIUM,
                            metric=f"{title}.{col}",
                            current_value=trend["last_value"],
                            previous_value=trend["first_value"],
                            change_pct=trend["change_pct"],
                            impact=f"{'Positive' if trend['direction'] == 'up' else 'Negative'} impact on {title}",
                        )
                    )

                # Growth rate analysis
                growth = compute_growth_rate(values)
                if growth["avg_growth"] != 0:
                    insights.append(
                        Insight(
                            id=_uid(),
                            type=(
                                InsightType.HIGHEST_GROWTH
                                if growth["avg_growth"] > 0
                                else InsightType.LOWEST_GROWTH
                            ),
                            title=f"{title} — {col} growth rate",
                            description=(
                                f"Average growth: {growth['avg_growth']:+.1f}%, "
                                f"range: [{growth['min_growth']:.1f}%, {growth['max_growth']:.1f}%]"
                            ),
                            evidence=[f"Average growth: {growth['avg_growth']:.1f}%"],
                            confidence=Confidence.MEDIUM,
                            metric=f"{title}.{col}",
                            current_value=growth["avg_growth"],
                            change_pct=growth["avg_growth"],
                        )
                    )

                # Volatility analysis
                vol = compute_volatility(values)
                if vol["volatility"] == "high":
                    insights.append(
                        Insight(
                            id=_uid(),
                            type=InsightType.NEGATIVE_TREND,
                            title=f"{title} — {col} high volatility",
                            description=(
                                f"{col} shows high volatility (CV={vol['cv']:.1f}%, "
                                f"max drawdown={vol['max_drawdown']:.1f}%)"
                            ),
                            evidence=[
                                f"CV: {vol['cv']:.1f}%",
                                f"Max drawdown: {vol['max_drawdown']:.1f}%",
                            ],
                            confidence=Confidence.HIGH,
                            metric=f"{title}.{col}",
                            impact="High volatility indicates instability",
                        )
                    )

            # Ranking analysis
            if len(rows) > 1:
                # Try to find name/label columns and numeric columns for ranking
                name_cols = [c for c in rows[0] if c not in ds_numeric]
                if name_cols and ds_numeric:
                    rank_col = ds_numeric[0]
                    name_col = name_cols[0]
                    ranked = rank_values(
                        [{name_col: r.get(name_col), rank_col: r.get(rank_col)} for r in rows],
                        rank_col,
                        top_n=3,
                    )
                    if ranked["top"]:
                        top_names = [str(r.get(name_col, "?")) for r in ranked["top"][:3]]
                        insights.append(
                            Insight(
                                id=_uid(),
                                type=InsightType.TOP_PRODUCT,
                                title=f"{title} — Top performers by {rank_col}",
                                description=f"Top performers: {', '.join(top_names)}",
                                evidence=[f"Top by {rank_col}: {', '.join(top_names)}"],
                                confidence=Confidence.HIGH,
                                metric=f"{title}.{rank_col}",
                                current_value=ranked["max_value"],
                            )
                        )

        return insights

    def _statistical_anomalies(
        self,
        datasets: dict[str, Any],
        numeric_cols: list[str],
        date_col: str | None,
    ) -> list[Anomaly]:
        """Detect anomalies using statistical methods."""
        all_anomalies: list[Anomaly] = []

        for ds_id, ds in datasets.items():
            rows = ds.get("rows", [])
            if not rows:
                continue

            ds_numeric, ds_date = self._extract_numeric_columns(rows)
            effective_date = ds_date[0] if ds_date else date_col

            raw_anomalies = detect_all_anomalies(rows, ds_numeric, effective_date)

            for raw in raw_anomalies:
                atype_map = {
                    "revenue_spike": AnomalyType.REVENUE_SPIKE,
                    "revenue_drop": AnomalyType.REVENUE_DROP,
                    "unexpected_sales": AnomalyType.UNEXPECTED_SALES,
                    "outlier": AnomalyType.OUTLIER,
                    "missing_values": AnomalyType.MISSING_VALUES,
                    "duplicate_records": AnomalyType.DUPLICATE_RECORDS,
                    "unusual_behavior": AnomalyType.UNUSUAL_BEHAVIOR,
                    "performance_degradation": AnomalyType.PERFORMANCE_DEGRADATION,
                }
                raw_type = raw.get("type", "outlier")
                anomaly_type = atype_map.get(raw_type, AnomalyType.OUTLIER)

                all_anomalies.append(
                    Anomaly(
                        id=_uid(),
                        type=anomaly_type,
                        title=f"{ds.get('title', ds_id)} — {raw.get('metric', 'data')} anomaly",
                        description=(
                            f"Detected {raw_type} in {raw.get('metric', 'data')}. "
                            f"Severity: {raw.get('severity', 'medium')}"
                        ),
                        severity=raw.get("severity", "medium"),
                        metric=raw.get("metric", ""),
                        expected_value=float(raw.get("expected", raw.get("median", 0))),
                        actual_value=float(raw.get("value", 0)),
                        deviation_pct=float(raw.get("deviation_pct", 0)),
                        confidence=(
                            Confidence.HIGH if raw.get("severity") == "high" else Confidence.MEDIUM
                        ),
                        evidence=[
                            f"{k}: {v}"
                            for k, v in raw.items()
                            if k not in ("type", "severity", "metric")
                        ],
                    )
                )

        return all_anomalies

    def _statistical_forecasts(
        self,
        datasets: dict[str, Any],
        numeric_cols: list[str],
        forecast_days: int,
    ) -> list[Forecast]:
        """Generate forecasts for numeric columns."""
        forecasts: list[Forecast] = []

        for ds_id, ds in datasets.items():
            rows = ds.get("rows", [])
            if not rows:
                continue

            ds_numeric, _ = self._extract_numeric_columns(rows)

            for col in ds_numeric:
                values = [r.get(col) for r in rows]
                result = generate_forecast(values, horizon=forecast_days, metric_name=col)

                if result.get("points"):
                    forecasts.append(
                        Forecast(
                            metric=f"{ds.get('title', ds_id)}.{col}",
                            horizon_days=forecast_days,
                            points=[
                                ForecastPoint(
                                    date=str(p.get("index", "")),
                                    value=p["value"],
                                    lower_bound=p.get("lower_bound", p["value"]),
                                    upper_bound=p.get("upper_bound", p["value"]),
                                )
                                for p in result["points"]
                            ],
                            trend=result.get("trend", ""),
                            seasonality_detected=result.get("seasonality_detected", False),
                            confidence=Confidence(result.get("confidence", "medium")),
                            accuracy_score=result.get("accuracy_score", 0),
                        )
                    )

        return forecasts

    # ------------------------------------------------------------------
    # Main analysis pipeline
    # ------------------------------------------------------------------

    async def analyze(
        self,
        dashboard_id: str,
        summary_type: Any = None,
        comparison: Any = None,
        forecast_days: int = 30,
        include_recommendations: bool = True,
        include_anomalies: bool = True,
        include_forecast: bool = True,
    ) -> dict[str, Any]:
        """Run the full analysis pipeline on a dashboard."""
        from app.ai.analytics.schemas import SummaryType

        start = time.monotonic()
        if summary_type is None:
            summary_type = SummaryType.EXECUTIVE_BRIEF

        try:
            dashboard = self._load_dashboard_data(dashboard_id)
        except ValueError as e:
            return {
                "success": False,
                "dashboard_id": dashboard_id,
                "error": str(e),
            }

        datasets = dashboard.get("datasets", {})
        all_rows, numeric_cols, date_col = self._flatten_datasets(datasets)
        data_context = self._build_data_context(datasets)

        # 1. Statistical analysis
        stat_insights = self._statistical_insights(datasets, all_rows, numeric_cols)

        # 2. Statistical anomaly detection
        stat_anomalies: list[Anomaly] = []
        if include_anomalies:
            stat_anomalies = self._statistical_anomalies(datasets, numeric_cols, date_col)

        # 3. Statistical forecasts
        stat_forecasts: list[Forecast] = []
        if include_forecast:
            stat_forecasts = self._statistical_forecasts(datasets, numeric_cols, forecast_days)

        # 4. LLM-enhanced insights (supplement statistical)
        llm_insights = await self._llm_insights(data_context)
        all_insights = stat_insights + llm_insights

        # 5. LLM-enhanced anomalies
        llm_anomalies: list[Anomaly] = []
        if include_anomalies:
            llm_anomalies = await self._llm_anomalies(data_context)
        all_anomalies = stat_anomalies + llm_anomalies

        # 6. Root cause analysis (if there are negative trends)
        root_causes: list[RootCause] = []
        neg_insights = [i for i in all_insights if i.type.value == "negative_trend"]
        if neg_insights:
            change_summary = "; ".join(f"{i.title}: {i.change_pct:.1f}%" for i in neg_insights[:5])
            root_causes = await self._llm_root_causes(data_context, data_context, change_summary)

        # 7. Best forecast for narrative
        best_forecast: Forecast | None = None
        if stat_forecasts:
            best_forecast = max(stat_forecasts, key=lambda f: f.accuracy_score)

        # 8. Recommendations
        recs: list = []
        if include_recommendations:
            recs = generate_recommendations(all_insights, all_anomalies, root_causes)

        # 9. Executive summary
        summary = await generate_summary(
            summary_type,
            all_insights,
            all_anomalies,
            recs,
            forecast_summary=best_forecast.model_dump() if best_forecast else None,
            provider=self._get_provider(),
        )

        # 10. Chart explanations
        chart_explanations: list[ChartExplanation] = []
        for ds_id, ds in datasets.items():
            title = ds.get("title", ds_id)
            chart_type = ds.get("chart_type", "table")
            rows = ds.get("rows", [])
            if not rows:
                continue

            data_summary = json.dumps(rows[:5], default=str)
            explanation = await self._llm_chart_explanation(title, chart_type, data_summary)
            chart_explanations.append(
                ChartExplanation(
                    chart_id=ds_id,
                    title=title,
                    meaning=explanation.get("meaning", ""),
                    action=explanation.get("action", ""),
                    importance=explanation.get("importance", ""),
                    confidence=Confidence(explanation.get("confidence", "medium")),
                )
            )

        # 11. Risk and opportunity scores
        risk_score = min(
            100,
            len([a for a in all_anomalies if a.severity == "high"]) * 15
            + len(neg_insights) * 10
            + len(root_causes) * 5,
        )
        opportunity_score = min(
            100,
            len([i for i in all_insights if i.type.value in ("positive_trend", "highest_growth")])
            * 15
            + len([r for r in recs if r.category == "growth"]) * 10,
        )

        elapsed = (time.monotonic() - start) * 1000

        return {
            "success": True,
            "dashboard_id": dashboard_id,
            "summary": summary.model_dump() if summary else None,
            "insights": [i.model_dump() for i in all_insights],
            "anomalies": [a.model_dump() for a in all_anomalies],
            "root_causes": [rc.model_dump() for rc in root_causes],
            "recommendations": [r.model_dump() for r in recs],
            "forecast": best_forecast.model_dump() if best_forecast else None,
            "chart_explanations": [ce.model_dump() for ce in chart_explanations],
            "risk_score": risk_score,
            "opportunity_score": opportunity_score,
            "analysis_time_ms": round(elapsed, 2),
        }

    # ------------------------------------------------------------------
    # Follow-up Q&A
    # ------------------------------------------------------------------

    async def followup(self, request: FollowUpRequest) -> dict[str, Any]:
        """Answer a follow-up question using dashboard context."""
        try:
            dashboard = self._load_dashboard_data(request.dashboard_id)
        except ValueError as e:
            return {"answer": f"Error: {e}", "confidence": "low"}

        datasets = dashboard.get("datasets", {})
        data_context = self._build_data_context(datasets)

        analysis_context = ""
        if request.context:
            analysis_context = json.dumps(request.context, default=str)[:4000]

        try:
            provider = self._get_provider()
            prompt = FOLLOWUP_PROMPT.format(
                data_context=data_context[:6000],
                analysis_context=analysis_context,
                question=request.question,
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            response = await provider.chat(messages)
            answer = response.get("content", "I could not generate an answer.")

            return {
                "answer": answer,
                "confidence": "medium",
                "evidence": [],
                "related_insights": [],
            }
        except Exception as e:  # noqa: BLE001
            return {
                "answer": f"I encountered an error while processing your question: {e}",
                "confidence": "low",
                "evidence": [],
                "related_insights": [],
            }
