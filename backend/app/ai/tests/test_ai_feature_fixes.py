"""Regression tests for the AI feature fixes found by the E2E feature sweep.

Covers: dashboard widget normalization (widget_id/kind contract), prediction
result schema (optional target/horizon), tolerant business recommendations,
lazy-engine inspection, copilot sql_query param tolerance, and workflow
creation with UUID primary keys.
"""

from __future__ import annotations

import uuid

import pytest

from app.ai.dashboard.service import _normalize_widgets
from app.ai.predictions.schemas import BusinessRecommendation, PredictionResult

ORG = str(uuid.uuid4())
USER = str(uuid.uuid4())


class TestDashboardWidgetNormalization:
    def test_planner_widgets_gain_widget_id_and_kind(self):
        widgets = [
            {"id": "kpi_1", "type": "kpi", "title": "Total Sales"},
            {"id": "chart_1", "type": "line", "title": "Sales trend"},
            {"id": "table_1", "type": "table", "title": "Breakdown"},
        ]
        out = _normalize_widgets(widgets)
        assert [w["widget_id"] for w in out] == ["kpi_1", "chart_1", "table_1"]
        assert [w["kind"] for w in out] == ["kpi", "chart", "table"]
        # original chart vocabulary is preserved in chart_config
        assert out[1]["chart_config"]["type"] == "line"

    def test_missing_or_duplicate_ids_are_repaired(self):
        widgets = [
            {"type": "bar"},
            {"type": "pie", "id": "dup"},
            {"type": "area", "id": "dup"},
        ]
        out = _normalize_widgets(widgets)
        ids = [w["widget_id"] for w in out]
        assert len(ids) == len(set(ids)), "widget ids must be unique"
        assert all(w["kind"] == "chart" for w in out)
        assert all(w["title"] for w in out)

    def test_unknown_type_falls_back_to_chart_kind(self):
        out = _normalize_widgets([{"id": "x", "type": "hologram"}])
        assert out[0]["kind"] == "chart"

    def test_non_dict_entries_are_dropped(self):
        out = _normalize_widgets(["junk", {"id": "w", "type": "kpi"}, None])
        assert len(out) == 1 and out[0]["widget_id"] == "w"


class TestPredictionSchemas:
    def test_prediction_result_can_be_built_before_target_assignment(self):
        # The forecast builders construct the result first and the orchestrator
        # assigns target/horizon right after — the fields must not be required.
        result = PredictionResult(
            prediction_id="p1",
            predictions=[],
        )
        result.target = "sales"
        result.horizon = "30_days"
        assert result.target == "sales"

    def test_business_recommendation_defaults(self):
        rec = BusinessRecommendation(recommendation="Increase stock")
        assert rec.category == "general"
        assert rec.impact == "medium"
        assert rec.confidence == "medium"
        assert rec.priority == "medium"


class TestLazyEngineInspection:
    def test_lazy_engine_unwraps_to_an_inspectable_engine(self):
        from sqlalchemy import inspect as sa_inspect

        from app.db.session import engine

        real = engine.unwrap()
        inspector = sa_inspect(real)
        assert len(inspector.get_table_names()) > 0

    def test_schema_explorer_works_with_the_lazy_engine(self):
        from app.ai.nlq.schema_explorer import SchemaExplorer
        from app.db.session import engine

        schema = SchemaExplorer(engine).get_schema()
        assert schema["tables"], "schema explorer must see database tables"


class TestCopilotTools:
    @pytest.mark.asyncio
    async def test_sql_query_without_question_fails_with_clear_error(self):
        from app.copilot.tools.registry import SQLQueryTool

        with pytest.raises(ValueError, match="question"):
            await SQLQueryTool().execute({}, {})

    @pytest.mark.asyncio
    async def test_sql_query_accepts_query_alias(self, monkeypatch):
        captured: dict = {}

        class FakeNL2SQL:
            def __init__(self, engine=None, organization_id=None):
                self.organization_id = organization_id

            async def query(self, question: str, include_chart: bool = True):
                captured["question"] = question
                return {"success": True, "sql": "SELECT 1", "rows": []}

        import app.ai.nlq.nl2sql_service as nl2sql_mod

        monkeypatch.setattr(nl2sql_mod, "NL2SQLService", FakeNL2SQL)
        from app.copilot.tools.registry import SQLQueryTool

        result = await SQLQueryTool().execute({"query": "How many organizations?"}, {})
        assert captured["question"] == "How many organizations?"
        assert result["type"] == "table"


class TestWorkflowIds:
    def test_workflow_create_uses_full_uuid_pk(self):
        """A truncated id ('xxxxxxxxxxx') used to fail the UUID column insert."""
        from app.workflows.schemas import StepDefinition, TriggerConfig, WorkflowCreateRequest
        from app.workflows.services.orchestrator import WorkflowOrchestrator

        svc = WorkflowOrchestrator()
        request = WorkflowCreateRequest(
            name=f"regression-{uuid.uuid4().hex[:6]}",
            description="regression test workflow",
            trigger=TriggerConfig(),
            steps=[
                StepDefinition(
                    name="analyze",
                    action_type="analyze_dataset",
                    config={"dataset_id": str(uuid.uuid4())},
                )
            ],
        )
        result = svc.create_workflow(request, user_id=USER, organization_id=ORG)
        assert result.get("success") is True, result
        wf_id = result["workflow_id"]
        # Must be a valid UUID (PostgreSQL UUID primary key)
        uuid.UUID(wf_id)
        svc.delete_workflow(wf_id, organization_id=ORG)
