from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    risk_level: str = "low"
    timeout_seconds: int = 120
    required_permissions: list[str] = []

    @abstractmethod
    async def execute(self, params: dict, context: dict) -> dict:
        """Execute the tool and return structured results."""

    def input_schema(self) -> dict:
        return {}

    def output_schema(self) -> dict:
        return {}


class SQLQueryTool(BaseTool):
    """NL-to-SQL query execution. Wraps existing NL2SQLService."""

    name = "sql_query"
    description = "Convert natural language to SQL and execute against the database"
    risk_level = "low"

    async def execute(self, params: dict, context: dict) -> dict:
        from app.ai.nlq.nl2sql_service import NL2SQLService
        from app.db.session import get_engine

        engine = get_engine()
        service = NL2SQLService(engine=engine)
        result = await service.query(
            question=params["question"],
            include_chart=params.get("include_chart", True),
        )
        return {"type": "table", "data": result}


class RAGQueryTool(BaseTool):
    """Knowledge base search. Wraps existing RAGService."""

    name = "rag_query"
    description = "Search the enterprise knowledge base for policies, documents, and procedures"
    risk_level = "low"

    async def execute(self, params: dict, context: dict) -> dict:
        from app.db.session import get_db_session
        from app.knowledge.schemas.answer import RAGQueryRequest
        from app.knowledge.services.rag_service import RAGService

        with get_db_session() as db:
            service = RAGService(db)
            request = RAGQueryRequest(
                query=params["query"],
                collection_ids=params.get("collection_ids"),
                top_k=params.get("top_k", 8),
            )
            result = await service.query(
                request,
                context["organization_id"],
                context["user_id"],
            )
            return {"type": "rag", "data": result}


class DashboardGeneratorTool(BaseTool):
    """Dashboard generation. Wraps existing AIDashboardService."""

    name = "dashboard_generator"
    description = "Generate an interactive dashboard from a natural language description"
    risk_level = "medium"

    async def execute(self, params: dict, context: dict) -> dict:
        from app.ai.dashboard.service import AIDashboardService
        from app.db.session import get_engine

        engine = get_engine()
        service = AIDashboardService(engine=engine)
        result = await service.generate(
            prompt=params["prompt"],
            organization_id=context.get("organization_id", ""),
        )
        return {"type": "dashboard", "data": result}


class ReportGeneratorTool(BaseTool):
    """Report generation. Wraps existing ReportGeneratorService."""

    name = "report_generator"
    description = "Generate a business report (executive, sales, financial, etc.)"
    risk_level = "medium"

    async def execute(self, params: dict, context: dict) -> dict:
        from app.ai.reports.services.report_service import ReportGeneratorService
        from app.db.session import get_db_session, get_engine

        engine = get_engine()
        with get_db_session() as db:
            service = ReportGeneratorService(engine=engine, db=db)
            result = await service.generate(
                prompt=params["prompt"],
                dashboard_id=params.get("dashboard_id"),
                report_type=params.get("report_type", "custom"),
                formats=params.get("formats", ["pdf"]),
                organization_id=context.get("organization_id", ""),
            )
            return {"type": "report", "data": result}


class ForecastTool(BaseTool):
    """Forecasting. Wraps existing prediction pipeline."""

    name = "forecast"
    description = "Generate forecasts for business metrics (revenue, sales, etc.)"
    risk_level = "low"

    async def execute(self, params: dict, context: dict) -> dict:
        from app.ai.predictions.services.orchestrator import predict_with_params

        result = await predict_with_params(
            dataset_id=params.get("dataset_id", ""),
            target=params.get("target", ""),
            horizon=params.get("horizon", "30_days"),
        )
        return {"type": "forecast", "data": result}


class BusinessAnalysisTool(BaseTool):
    """Business analysis. Wraps existing BusinessAnalystService."""

    name = "business_analysis"
    description = "Analyze business data: KPIs, trends, anomalies, root causes, recommendations"
    risk_level = "low"

    async def execute(self, params: dict, context: dict) -> dict:
        from app.ai.analytics.service import BusinessAnalystService
        from app.db.session import get_db_session, get_engine

        engine = get_engine()
        with get_db_session() as db:
            service = BusinessAnalystService(engine=engine, db=db)
            result = await service.analyze(
                dashboard_id=params.get("dashboard_id", ""),
                summary_type=params.get("summary_type", "executive_brief"),
                comparison=params.get("comparison"),
            )
            return {"type": "analysis", "data": result}


class DataProfileTool(BaseTool):
    """Data profiling. Wraps existing data engineering APIs."""

    name = "data_profile"
    description = "Profile a dataset to understand its structure, quality, and characteristics"
    risk_level = "low"

    async def execute(self, params: dict, context: dict) -> dict:
        from app.ai.data_engineering.services.data_loader import DataLoader
        from app.db.session import get_engine

        engine = get_engine()
        loader = DataLoader(engine)
        result = await loader.profile_dataset(params.get("dataset_id", ""))
        return {"type": "profile", "data": result}


class WorkflowGeneratorTool(BaseTool):
    """Workflow generation. Wraps existing workflow engine."""

    name = "workflow_generator"
    description = "Create automated workflows (schedules, alerts, reports)"
    risk_level = "high"

    async def execute(self, params: dict, context: dict) -> dict:
        from app.db.session import get_db_session
        from app.workflows.services.orchestrator import WorkflowOrchestrator

        with get_db_session() as db:
            orchestrator = WorkflowOrchestrator(db)
            result = await orchestrator.create_workflow(
                name=params.get("name", "Copilot Workflow"),
                description=params.get("description", ""),
                steps=params.get("steps", []),
                trigger=params.get("trigger", {}),
                organization_id=context.get("organization_id", ""),
            )
            return {"type": "workflow", "data": result}


class NotificationTool(BaseTool):
    """Send notifications."""

    name = "notification"
    description = "Send an in-app notification to the user"
    risk_level = "low"

    async def execute(self, params: dict, context: dict) -> dict:
        from app.admin.services.platform import PlatformAdmin
        from app.db.session import get_db_session

        with get_db_session():
            platform = PlatformAdmin()
            platform.notifications.create(
                user_id=context.get("user_id", ""),
                title=params.get("title", "Copilot Notification"),
                message=params.get("message", ""),
            )
        return {"type": "notification", "data": {"sent": True}}


class MLOpsTool(BaseTool):
    """MLOps model lifecycle operations."""

    name = "mlops"
    description = (
        "Manage ML models: register, train, evaluate, deploy, monitor, detect drift, rollback"
    )
    risk_level = "high"

    async def execute(self, params: dict, context: dict) -> dict:
        from app.db.session import get_db_session
        from app.mlops.services.lifecycle_service import LifecycleService
        from app.mlops.services.model_registry import ModelRegistryService

        action = params.get("action", "list_models")
        org_id = context.get("organization_id", "")

        with get_db_session() as db:
            if action == "list_models":
                service = ModelRegistryService(db)
                models = service.list_models(org_id)
                return {
                    "type": "mlops",
                    "data": {
                        "models": [
                            {
                                "id": m.id,
                                "name": m.name,
                                "status": m.status,
                                "model_type": m.model_type,
                            }
                            for m in models
                        ],
                        "total": len(models),
                    },
                }
            elif action == "model_lifecycle":
                service = LifecycleService(db)
                result = service.get_model_lifecycle(params.get("model_id", ""), org_id)
                return {"type": "mlops", "data": result}
            elif action == "overview":
                service = LifecycleService(db)
                result = service.get_overview(org_id)
                return {"type": "mlops", "data": result}
            elif action == "rollback":
                from app.mlops.services.rollback_service import RollbackService

                service = RollbackService(db)
                result = service.rollback(
                    params.get("model_id", ""),
                    org_id,
                    params.get("target_version_id", ""),
                )
                return {"type": "mlops", "data": result}
            else:
                return {"type": "mlops", "data": {"error": f"Unknown action: {action}"}}


class ToolRegistry:
    _instance: ToolRegistry | None = None

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._register_defaults()

    @classmethod
    def get_instance(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _register_defaults(self) -> None:
        for tool_cls in [
            SQLQueryTool,
            RAGQueryTool,
            DashboardGeneratorTool,
            ReportGeneratorTool,
            ForecastTool,
            BusinessAnalysisTool,
            DataProfileTool,
            WorkflowGeneratorTool,
            NotificationTool,
            MLOpsTool,
        ]:
            tool = tool_cls()
            self._tools[tool.name] = tool

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "risk_level": t.risk_level,
            }
            for t in self._tools.values()
        ]

    def has(self, name: str) -> bool:
        return name in self._tools

    def get_risk_level(self, name: str) -> str:
        tool = self.get(name)
        return tool.risk_level if tool else "unknown"
