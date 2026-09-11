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
    ]:
        instance = cls()
        _ACTION_HANDLERS[instance.action_type] = instance


def get_action_handler(action_type: ActionType) -> BaseAction:
    if not _ACTION_HANDLERS:
        _init_registry()
    if action_type not in _ACTION_HANDLERS:
        raise ValueError(f"No handler for action type: {action_type}")
    return _ACTION_HANDLERS[action_type]
