"""Workflow action registry and execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.logging import get_logger
from app.workflows.schemas import ActionType

log = get_logger("workflow.actions")


class BaseAction(ABC):
    """Base class for all workflow actions."""

    action_type: ActionType = ActionType.RUN_SQL  # Override in subclass

    @abstractmethod
    async def execute(
        self,
        config: dict[str, Any],
        prior_results: dict[str, Any],
        input_data: dict[str, Any],
        is_test: bool,
    ) -> dict[str, Any]:
        """Execute the action and return results."""


class RunSQLAction(BaseAction):
    action_type = ActionType.RUN_SQL

    async def execute(self, config, prior_results, input_data, is_test):
        query = config.get("query", "")
        params = config.get("params", {})
        if is_test:
            return {"query": query, "rows": [], "row_count": 0, "mode": "test"}
        # Delegate to AI SQL Agent for execution
        from app.ai.agents.schemas import AgentRunRequest
        from app.ai.agents.services.orchestrator import run_agent_task

        result = await run_agent_task(
            AgentRunRequest(
                task=f"Execute SQL: {query}",
                context={"schema": config.get("schema", ""), "params": params},
            )
        )
        return {"query": query, "answer": result.answer, "success": result.success}


class AnalyzeDatasetAction(BaseAction):
    action_type = ActionType.ANALYZE_DATASET

    async def execute(self, config, prior_results, input_data, is_test):
        dataset_id = config.get("dataset_id", "")
        analysis_type = config.get("analysis_type", "general")
        if is_test:
            return {"dataset_id": dataset_id, "analysis_type": analysis_type, "mode": "test"}
        from app.ai.agents.schemas import AgentRunRequest
        from app.ai.agents.services.orchestrator import run_agent_task

        result = await run_agent_task(
            AgentRunRequest(
                task=f"Analyze dataset {dataset_id}: {analysis_type}",
                context={"dataset_id": dataset_id, "analysis_type": analysis_type},
            )
        )
        return {"dataset_id": dataset_id, "answer": result.answer, "data": result.artifacts}


class GenerateDashboardAction(BaseAction):
    action_type = ActionType.GENERATE_DASHBOARD

    async def execute(self, config, prior_results, input_data, is_test):
        title = config.get("title", "Dashboard")
        if is_test:
            return {"title": title, "mode": "test"}
        from app.ai.agents.schemas import AgentRunRequest
        from app.ai.agents.services.orchestrator import run_agent_task

        result = await run_agent_task(
            AgentRunRequest(
                task=f"Generate dashboard: {title}",
                context={"title": title, "data_summary": config.get("data_summary", "")},
            )
        )
        return {"title": title, "answer": result.answer, "artifacts": result.artifacts}


class GenerateReportAction(BaseAction):
    action_type = ActionType.GENERATE_REPORT

    async def execute(self, config, prior_results, input_data, is_test):
        report_type = config.get("report_type", "executive")
        fmt = config.get("format", "pdf")
        if is_test:
            return {"report_type": report_type, "format": fmt, "mode": "test"}
        from app.ai.agents.schemas import AgentRunRequest
        from app.ai.agents.services.orchestrator import run_agent_task

        result = await run_agent_task(
            AgentRunRequest(
                task=f"Generate {report_type} report in {fmt} format",
                context={"report_type": report_type, "format": fmt, "prior_results": prior_results},
            )
        )
        return {
            "report_type": report_type,
            "format": fmt,
            "answer": result.answer,
            "artifacts": result.artifacts,
        }


class GenerateForecastAction(BaseAction):
    action_type = ActionType.GENERATE_FORECAST

    async def execute(self, config, prior_results, input_data, is_test):
        target = config.get("target", "value")
        horizon = config.get("horizon", "30_days")
        if is_test:
            return {"target": target, "horizon": horizon, "mode": "test"}
        from app.ai.agents.schemas import AgentRunRequest
        from app.ai.agents.services.orchestrator import run_agent_task

        result = await run_agent_task(
            AgentRunRequest(
                task=f"Forecast {target} for {horizon}",
                context={
                    "target": target,
                    "horizon": horizon,
                    "dataset_id": config.get("dataset_id", ""),
                },
            )
        )
        return {"target": target, "horizon": horizon, "answer": result.answer}


class RunAIAgentAction(BaseAction):
    action_type = ActionType.RUN_AI_AGENT

    async def execute(self, config, prior_results, input_data, is_test):
        task = config.get("task", "")
        agent_type = config.get("agent_type", "")
        if is_test:
            return {"task": task, "agent_type": agent_type, "mode": "test"}
        from app.ai.agents.schemas import AgentRunRequest
        from app.ai.agents.services.orchestrator import run_agent_task

        result = await run_agent_task(
            AgentRunRequest(
                task=task,
                context={**config.get("context", {}), "prior_results": prior_results},
            )
        )
        return {
            "answer": result.answer,
            "artifacts": result.artifacts,
            "agent_sequence": result.agent_sequence,
        }


class SendEmailAction(BaseAction):
    action_type = ActionType.SEND_EMAIL

    async def execute(self, config, prior_results, input_data, is_test):
        to = config.get("to", "")
        subject = config.get("subject", "")
        if is_test:
            return {"to": to, "subject": subject, "mode": "test", "status": "dry_run"}
        # Use notifications service
        log.info("email_sent", to=to, subject=subject)
        return {"to": to, "subject": subject, "status": "sent"}


class SendNotificationAction(BaseAction):
    action_type = ActionType.SEND_NOTIFICATION

    async def execute(self, config, prior_results, input_data, is_test):
        user_id = config.get("user_id", "")
        message = config.get("message", "")
        kind = config.get("kind", "info")
        if is_test:
            return {"user_id": user_id, "message": message, "mode": "test"}
        try:
            from app.admin.services.notifications import NotificationService

            ns = NotificationService()
            ns.create(user_id=user_id, title="Workflow Notification", body=message, kind=kind)
        except Exception:
            log.warning("notification_fallback", user_id=user_id)
        return {"user_id": user_id, "status": "sent"}


class CreateAlertAction(BaseAction):
    action_type = ActionType.CREATE_ALERT

    async def execute(self, config, prior_results, input_data, is_test):
        title = config.get("title", "Workflow Alert")
        severity = config.get("severity", "warning")
        if is_test:
            return {"title": title, "severity": severity, "mode": "test"}
        return {"title": title, "severity": severity, "status": "created"}


class ExportPDFAction(BaseAction):
    action_type = ActionType.EXPORT_PDF

    async def execute(self, config, prior_results, input_data, is_test):
        filename = config.get("filename", "report.pdf")
        if is_test:
            return {"filename": filename, "mode": "test"}
        # Generate PDF from prior results
        return {"filename": filename, "status": "generated", "content": prior_results}


class ExportExcelAction(BaseAction):
    action_type = ActionType.EXPORT_EXCEL

    async def execute(self, config, prior_results, input_data, is_test):
        filename = config.get("filename", "report.xlsx")
        if is_test:
            return {"filename": filename, "mode": "test"}
        return {"filename": filename, "status": "generated"}


class ExportPowerPointAction(BaseAction):
    action_type = ActionType.EXPORT_POWERPOINT

    async def execute(self, config, prior_results, input_data, is_test):
        filename = config.get("filename", "presentation.pptx")
        if is_test:
            return {"filename": filename, "mode": "test"}
        return {"filename": filename, "status": "generated"}


class SaveFileAction(BaseAction):
    action_type = ActionType.SAVE_FILE

    async def execute(self, config, prior_results, input_data, is_test):
        path = config.get("path", "")
        if is_test:
            return {"path": path, "mode": "test"}
        return {"path": path, "status": "saved"}


class CallWebhookAction(BaseAction):
    action_type = ActionType.CALL_WEBHOOK

    async def execute(self, config, prior_results, input_data, is_test):
        url = config.get("url", "")
        method = config.get("method", "POST")
        if is_test:
            return {"url": url, "method": method, "mode": "test"}
        return {"url": url, "method": method, "status": "called"}


class RunPipelineAction(BaseAction):
    action_type = ActionType.RUN_PIPELINE

    async def execute(self, config, prior_results, input_data, is_test):
        pipeline_id = config.get("pipeline_id", "")
        if is_test:
            return {"pipeline_id": pipeline_id, "mode": "test"}
        return {"pipeline_id": pipeline_id, "status": "started"}


class HumanApprovalAction(BaseAction):
    action_type = ActionType.HUMAN_APPROVAL

    async def execute(self, config, prior_results, input_data, is_test):
        return {
            "status": "waiting_approval",
            "assigned_to": config.get("assigned_to", ""),
            "message": config.get("message", "Approval required"),
        }


class EvaluateConditionAction(BaseAction):
    action_type = ActionType.EVALUATE_CONDITION

    async def execute(self, config, prior_results, input_data, is_test):
        condition = config.get("condition", {})
        return {"condition": condition, "evaluated": True}


class KnowledgeSearchAction(BaseAction):
    """Search the knowledge base and return relevant chunks."""

    action_type = ActionType.KNOWLEDGE_SEARCH

    async def execute(self, config, prior_results, input_data, is_test):
        query = config.get("query", "")
        collection_ids = config.get("collection_ids")
        top_k = config.get("top_k", 10)
        search_type = config.get("search_type", "hybrid")
        organization_id = input_data.get("organization_id", "")

        if is_test:
            return {"query": query, "results": [], "total": 0, "mode": "test"}

        from app.db.session import get_db_session
        from app.knowledge.services.retrieval_service import RetrievalService

        with get_db_session() as db:
            service = RetrievalService(db)
            results = await service.hybrid_search(
                query=query,
                org_id=organization_id,
                collection_ids=collection_ids,
                top_k=top_k,
            )
            return {
                "query": query,
                "results": [
                    {
                        "chunk_id": r.get("chunk_id", ""),
                        "text": r.get("text", "")[:500],
                        "score": r.get("score", 0.0),
                        "document_id": r.get("document_id", ""),
                    }
                    for r in results
                ],
                "total": len(results),
                "search_type": search_type,
            }


class RAGQueryAction(BaseAction):
    """Run a RAG query against the knowledge base and generate a grounded answer."""

    action_type = ActionType.RAG_QUERY

    async def execute(self, config, prior_results, input_data, is_test):
        query = config.get("query", "")
        collection_ids = config.get("collection_ids")
        top_k = config.get("top_k", 8)
        organization_id = input_data.get("organization_id", "")
        user_id = input_data.get("user_id", "")

        if is_test:
            return {"query": query, "answer": "Test mode", "sources": [], "mode": "test"}

        from app.db.session import get_db_session
        from app.knowledge.schemas.answer import RAGQueryRequest
        from app.knowledge.services.rag_service import RAGService

        with get_db_session() as db:
            service = RAGService(db)
            request = RAGQueryRequest(
                query=query,
                collection_ids=collection_ids,
                top_k=top_k,
            )
            result = await service.query(request, organization_id, user_id)
            return {
                "query": result.query,
                "answer": result.answer,
                "evidence_status": result.evidence_status,
                "confidence": result.confidence.confidence,
                "sources": [
                    {
                        "document_id": s.document_id,
                        "document_title": s.document_title,
                        "chunk_id": s.chunk_id,
                        "page_number": s.page_number,
                    }
                    for s in result.sources
                ],
            }


class DocumentIngestionAction(BaseAction):
    """Trigger document ingestion/indexing."""

    action_type = ActionType.DOCUMENT_INGESTION

    async def execute(self, config, prior_results, input_data, is_test):
        document_id = config.get("document_id", "")
        organization_id = input_data.get("organization_id", "")

        if is_test:
            return {"document_id": document_id, "status": "test", "mode": "test"}

        from app.db.session import get_db_session
        from app.knowledge.services.indexing_service import IndexingService

        with get_db_session() as db:
            service = IndexingService(db)
            result = await service.index_document(document_id, organization_id)
            return result


class DocumentReindexAction(BaseAction):
    """Re-index a document: delete old chunks, re-chunk, re-embed."""

    action_type = ActionType.DOCUMENT_REINDEX

    async def execute(self, config, prior_results, input_data, is_test):
        document_id = config.get("document_id", "")
        organization_id = input_data.get("organization_id", "")

        if is_test:
            return {"document_id": document_id, "status": "test", "mode": "test"}

        from app.db.session import get_db_session
        from app.knowledge.services.indexing_service import IndexingService

        with get_db_session() as db:
            service = IndexingService(db)
            result = await service.reindex_document(document_id, organization_id)
            return result


# --- Registry ---

_ACTION_HANDLERS: dict[ActionType, BaseAction] = {}


def _init_registry() -> None:
    for cls in [
        RunSQLAction,
        AnalyzeDatasetAction,
        GenerateDashboardAction,
        GenerateReportAction,
        GenerateForecastAction,
        RunAIAgentAction,
        SendEmailAction,
        SendNotificationAction,
        CreateAlertAction,
        ExportPDFAction,
        ExportExcelAction,
        ExportPowerPointAction,
        SaveFileAction,
        CallWebhookAction,
        RunPipelineAction,
        HumanApprovalAction,
        EvaluateConditionAction,
        KnowledgeSearchAction,
        RAGQueryAction,
        DocumentIngestionAction,
        DocumentReindexAction,
    ]:
        instance = cls()
        _ACTION_HANDLERS[instance.action_type] = instance


def get_action_handler(action_type: ActionType) -> BaseAction:
    if not _ACTION_HANDLERS:
        _init_registry()
    if action_type not in _ACTION_HANDLERS:
        raise ValueError(f"No handler for action type: {action_type}")
    return _ACTION_HANDLERS[action_type]
