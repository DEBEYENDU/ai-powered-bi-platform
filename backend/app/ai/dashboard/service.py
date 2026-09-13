"""AI Dashboard Generator service - orchestrates the full pipeline."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.ai.dashboard.layout_generator import LayoutGenerator
from app.ai.dashboard.models import DashboardVersion
from app.ai.dashboard.planner import DashboardPlanner
from app.ai.dashboard.validator import DashboardValidator
from app.ai.dashboard.widget_generator import WidgetGenerator
from app.ai.nlq.schema_explorer import SchemaExplorer
from app.ai.providers.registry import get_provider
from app.dashboards import service as dashboard_service


class AIDashboardService:
    """Orchestrates AI dashboard generation, improvement, and explanation."""

    def __init__(self, engine: Engine, db: Session | None = None) -> None:
        self.engine = engine
        self.db = db
        self.provider = get_provider()
        self.model = ""
        self.explorer = SchemaExplorer(engine)
        self.planner = DashboardPlanner(self.provider, self.model)
        self.widget_gen = WidgetGenerator(self.provider, self.model)
        self.layout_gen = LayoutGenerator()
        self.validator = DashboardValidator(engine)

    def _schema_text(self) -> str:
        return self.explorer.get_schema_text()

    async def generate(
        self,
        prompt: str,
        organization_id: str = "",
        save: bool = True,
    ) -> dict[str, Any]:
        """Generate a complete dashboard from a natural language prompt."""
        t0 = time.time()
        schema_text = self._schema_text()

        plan = await self.planner.plan(prompt, schema_text)

        widgets = plan.get("widgets", [])
        if widgets:
            widgets = await self.widget_gen.generate_widgets_batch(widgets, schema_text)

        layout = self.layout_gen.generate_layout(widgets)

        dashboard_data = {
            "title": plan.get("title", "AI Generated Dashboard"),
            "description": plan.get("description", ""),
            "widgets": widgets,
            "layout": layout,
            "filters": plan.get("filters", []),
            "theme": plan.get("theme", {}),
        }

        issues = self.validator.validate_dashboard({"widgets": widgets})
        errors = [i for i in issues if i["severity"] == "error"]
        if errors:
            dashboard_data["validation_errors"] = errors

        dashboard_id = None
        if save:
            dashboard_id = self._save_dashboard(dashboard_data, prompt, organization_id)

        elapsed = round((time.time() - t0) * 1000, 2)

        return {
            "success": True,
            "dashboard_id": dashboard_id,
            "title": dashboard_data["title"],
            "description": dashboard_data["description"],
            "widgets": widgets,
            "layout": layout,
            "filters": dashboard_data["filters"],
            "theme": dashboard_data["theme"],
            "generation_time_ms": elapsed,
            "error": None,
        }

    async def improve(
        self,
        dashboard_id: str,
        instruction: str,
    ) -> dict[str, Any]:
        """Improve an existing dashboard based on natural language instruction."""
        schema_text = self._schema_text()

        current = dashboard_service.get_dashboard(dashboard_id)
        if not current:
            return {"success": False, "error": "Dashboard not found"}

        improved = await self.planner.improve(current, instruction, schema_text)

        widgets = improved.get("widgets", [])
        if widgets:
            widgets = await self.widget_gen.generate_widgets_batch(widgets, schema_text)

        layout = self.layout_gen.generate_layout(widgets)

        dashboard_data = {
            "title": improved.get("title", current.get("name", "Dashboard")),
            "description": improved.get("description", ""),
            "widgets": widgets,
            "layout": layout,
            "filters": improved.get("filters", []),
            "theme": improved.get("theme", {}),
        }

        dashboard_service.update_dashboard(
            dashboard_id,
            {
                "name": dashboard_data["title"],
                "description": dashboard_data["description"],
                "widgets": widgets,
                "layout": layout,
                "filters": dashboard_data["filters"],
            },
        )

        self._save_version(dashboard_id, dashboard_data, instruction)

        return {
            "success": True,
            "dashboard_id": dashboard_id,
            "title": dashboard_data["title"],
            "description": dashboard_data["description"],
            "widgets": widgets,
            "layout": layout,
            "change_summary": instruction,
            "error": None,
        }

    async def explain(
        self,
        dashboard_id: str | None = None,
        widgets: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate explanations for dashboard widgets."""
        if dashboard_id:
            current = dashboard_service.get_dashboard(dashboard_id)
            if not current:
                return []
            widgets = current.get("widgets", [])

        if not widgets:
            return []

        explanations = await self.planner.explain(widgets)
        return explanations

    def get_versions(self, dashboard_id: str) -> list[dict[str, Any]]:
        """Get version history for a dashboard."""
        if not self.db:
            return []
        from sqlalchemy import select

        stmt = (
            select(DashboardVersion)
            .where(DashboardVersion.dashboard_id == dashboard_id)
            .order_by(DashboardVersion.version_number.desc())
        )
        versions = self.db.scalars(stmt).all()
        return [
            {
                "id": v.id,
                "version_number": v.version_number,
                "title": v.title,
                "change_summary": v.change_summary,
                "created_at": v.created_at.isoformat() if v.created_at else "",
            }
            for v in versions
        ]

    def rollback_version(self, dashboard_id: str, version_id: str) -> dict[str, Any] | None:
        """Rollback a dashboard to a previous version."""
        if not self.db:
            return None
        version = self.db.get(DashboardVersion, version_id)
        if not version or version.dashboard_id != dashboard_id:
            return None

        dashboard_service.update_dashboard(
            dashboard_id,
            {
                "name": version.title,
                "description": version.description,
                "widgets": version.widgets,
                "layout": version.layout,
                "filters": version.filters,
            },
        )
        return {"rolled_back_to": version.version_number}

    def _save_dashboard(
        self,
        data: dict[str, Any],
        prompt: str,
        organization_id: str,
    ) -> str:
        """Save generated dashboard to the database."""
        result = dashboard_service.create_dashboard(
            {
                "name": data["title"],
                "description": data.get("description", ""),
                "organization_id": organization_id,
                "layout": data.get("layout", {}),
                "widgets": data.get("widgets", []),
                "filters": data.get("filters", {}),
            }
        )
        dashboard_id = result.get("id", "")

        if dashboard_id and self.db:
            self._save_version(dashboard_id, data, prompt)

        return dashboard_id

    def _save_version(
        self,
        dashboard_id: str,
        data: dict[str, Any],
        change_summary: str,
    ) -> None:
        """Save a version snapshot."""
        if not self.db:
            return

        from sqlalchemy import func, select

        stmt = select(func.coalesce(func.max(DashboardVersion.version_number), 0)).where(
            DashboardVersion.dashboard_id == dashboard_id
        )
        max_ver = self.db.scalar(stmt) or 0

        version = DashboardVersion(
            id=str(uuid4()),
            dashboard_id=dashboard_id,
            version_number=max_ver + 1,
            title=data.get("title", ""),
            description=data.get("description", ""),
            widgets=data.get("widgets", []),
            layout=data.get("layout", {}),
            filters=data.get("filters", {}),
            theme=data.get("theme", {}),
            prompt=change_summary,
            change_summary=change_summary,
        )
        self.db.add(version)
        self.db.flush()
