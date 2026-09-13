from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.copilot.models.session import CopilotSession, CopilotTask, CopilotTaskStep
from app.copilot.schemas.response import CopilotStepResult, CopilotTaskResponse
from app.copilot.services.context_service import ContextService
from app.copilot.services.executor_service import ExecutionEngine
from app.copilot.services.intent_service import IntentService
from app.copilot.services.planner_service import PlannerService
from app.copilot.services.reasoning_service import ReasoningService
from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("copilot.service")


class CopilotService:
    def __init__(self, db: Session):
        self.db = db
        self.intent_service = IntentService()
        self.planner_service = PlannerService()
        self.execution_engine = ExecutionEngine()
        self.reasoning_service = ReasoningService()
        self.context_service = ContextService(db)
        self.settings = get_settings()

    async def process_query(
        self,
        query: str,
        user: dict[str, Any],
        organization_id: str,
        session_id: str | None = None,
    ) -> CopilotTaskResponse:
        """Full copilot pipeline: intent -> plan -> execute -> reason -> respond."""
        start_time = time.time()
        user_id = user.get("sub") or user.get("user_id", "")

        session = self._get_or_create_session(session_id, user_id, organization_id)

        task = CopilotTask(
            session_id=session.id,
            organization_id=organization_id,
            user_id=user_id,
            request=query,
            status="planning",
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        try:
            context = await self.context_service.collect_context(user, organization_id, session.id)

            intent = await self.intent_service.detect_intent(query, context)
            task.intent = intent.intent
            task.intent_confidence = intent.confidence

            if intent.requires_clarification:
                task.status = "awaiting_clarification"
                self.db.commit()
                return CopilotTaskResponse(
                    task_id=task.id,
                    session_id=session.id,
                    status="awaiting_clarification",
                    request=query,
                    intent=intent.intent,
                    intent_confidence=intent.confidence,
                    answer=intent.clarification_question or "I need more information to proceed.",
                )

            plan = await self.planner_service.create_plan(query, intent, context)
            task.plan_json = json.dumps(plan.model_dump(), default=str)
            task.total_steps = len(plan.steps)
            task.status = "executing"
            task.started_at = datetime.utcnow()
            self.db.commit()

            for i, step in enumerate(plan.steps):
                db_step = CopilotTaskStep(
                    task_id=task.id,
                    step_index=i,
                    tool_name=step.tool,
                    purpose=step.purpose,
                    input_json=json.dumps(step.params, default=str),
                    status="pending",
                )
                self.db.add(db_step)
            self.db.commit()

            def on_step_complete(step_result: CopilotStepResult):
                for db_step in self.db.query(CopilotTaskStep).filter_by(task_id=task.id):
                    if db_step.tool_name == step_result.tool_name and db_step.status == "pending":
                        db_step.status = step_result.status
                        db_step.output_json = (
                            json.dumps(step_result.result, default=str)
                            if step_result.result
                            else None
                        )
                        db_step.error_message = step_result.error
                        db_step.duration_ms = (
                            int(step_result.duration_ms) if step_result.duration_ms else None
                        )
                        db_step.completed_at = datetime.utcnow()
                        break
                task.completed_steps = sum(
                    1
                    for s in self.db.query(CopilotTaskStep).filter_by(task_id=task.id)
                    if s.status in ("completed", "failed", "skipped")
                )
                self.db.commit()

            step_results, tools_used = await self.execution_engine.execute_plan(
                plan, context, on_step_complete
            )

            task.status = "validating"
            self.db.commit()

            reasoning = await self.reasoning_service.reason(query, plan, step_results)

            answer_parts = self._build_answer_parts(reasoning, step_results)

            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.result_json = json.dumps(
                {
                    "answer": reasoning.get("answer", ""),
                    "key_findings": reasoning.get("key_findings", []),
                    "confidence": reasoning.get("confidence", 0.5),
                },
                default=str,
            )
            task.tools_used = ",".join(tools_used)
            self.db.commit()

            session.message_count += 1
            session.updated_at = datetime.utcnow()
            self.db.commit()

            total_ms = (time.time() - start_time) * 1000
            log.info(
                "copilot_completed task_id=%s intent=%s steps=%d tools=%s duration_ms=%.0f",
                task.id,
                intent.intent,
                len(step_results),
                tools_used,
                total_ms,
            )

            return CopilotTaskResponse(
                task_id=task.id,
                session_id=session.id,
                status="completed",
                request=query,
                intent=intent.intent,
                intent_confidence=intent.confidence,
                steps=step_results,
                answer=reasoning.get("answer", ""),
                answer_parts=answer_parts,
                tools_used=tools_used,
                total_steps=task.total_steps,
                completed_steps=task.completed_steps,
                created_at=str(task.created_at),
                completed_at=str(task.completed_at),
            )

        except Exception as exc:
            task.status = "failed"
            task.error_message = str(exc)
            task.completed_at = datetime.utcnow()
            self.db.commit()
            log.error("copilot_failed task_id=%s error=%s", task.id, str(exc))

            return CopilotTaskResponse(
                task_id=task.id,
                session_id=session.id,
                status="failed",
                request=query,
                error=str(exc),
                created_at=str(task.created_at),
            )

    def _get_or_create_session(self, session_id, user_id, organization_id) -> CopilotSession:
        if session_id:
            session = self.db.get(CopilotSession, session_id)
            if session and session.organization_id == organization_id:
                return session
        session = CopilotSession(
            organization_id=organization_id,
            user_id=user_id,
            title=None,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def _build_answer_parts(
        self, reasoning: dict, step_results: list[CopilotStepResult]
    ) -> list[dict]:
        """Build structured answer parts for the frontend."""
        parts = []

        if reasoning.get("answer"):
            parts.append({"type": "text", "content": reasoning["answer"]})

        if reasoning.get("key_findings"):
            parts.append({"type": "findings", "items": reasoning["key_findings"]})

        for sr in step_results:
            if sr.status == "completed" and sr.result:
                data = sr.result.get("data", sr.result)
                if isinstance(data, dict):
                    if data.get("rows"):
                        parts.append(
                            {
                                "type": "table",
                                "columns": data.get("columns", []),
                                "rows": data["rows"][:50],
                                "row_count": data.get("row_count", len(data["rows"])),
                                "source": sr.tool_name,
                            }
                        )
                    if data.get("chart_recommendation"):
                        parts.append(
                            {
                                "type": "chart",
                                "config": data["chart_recommendation"],
                                "source": sr.tool_name,
                            }
                        )
                    if "insights" in data:
                        parts.append(
                            {"type": "insights", "items": data["insights"], "source": sr.tool_name}
                        )
                    if "forecast" in data:
                        parts.append(
                            {"type": "forecast", "data": data["forecast"], "source": sr.tool_name}
                        )
                    if "sources" in data:
                        parts.append({"type": "citations", "items": data["sources"]})
                    if "sections" in data:
                        parts.append({"type": "report", "data": data, "source": sr.tool_name})

        if reasoning.get("caveats"):
            parts.append({"type": "warning", "items": reasoning["caveats"]})

        return parts

    def get_task(self, task_id: str, organization_id: str) -> CopilotTaskResponse | None:
        task = self.db.get(CopilotTask, task_id)
        if not task or task.organization_id != organization_id:
            return None
        steps = [
            CopilotStepResult(
                step_id=s.id,
                tool_name=s.tool_name,
                purpose=s.purpose or "",
                status=s.status,
                result=json.loads(s.output_json) if s.output_json else None,
                error=s.error_message,
                duration_ms=float(s.duration_ms) if s.duration_ms else None,
            )
            for s in self.db.query(CopilotTaskStep)
            .filter_by(task_id=task.id)
            .order_by(CopilotTaskStep.step_index)
        ]
        return CopilotTaskResponse(
            task_id=task.id,
            session_id=task.session_id,
            status=task.status,
            request=task.request,
            intent=task.intent,
            intent_confidence=task.intent_confidence,
            steps=steps,
            answer=json.loads(task.result_json).get("answer") if task.result_json else None,
            tools_used=(task.tools_used or "").split(",") if task.tools_used else [],
            total_steps=task.total_steps,
            completed_steps=task.completed_steps,
            error=task.error_message,
            created_at=str(task.created_at),
            completed_at=str(task.completed_at) if task.completed_at else None,
        )

    def list_sessions(self, user_id: str, organization_id: str) -> list[dict]:
        sessions = (
            self.db.query(CopilotSession)
            .filter(
                CopilotSession.user_id == user_id,
                CopilotSession.organization_id == organization_id,
            )
            .order_by(CopilotSession.created_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": s.id,
                "title": s.title,
                "message_count": s.message_count,
                "created_at": str(s.created_at),
            }
            for s in sessions
        ]

    def cancel_task(self, task_id: str, organization_id: str) -> bool:
        task = self.db.get(CopilotTask, task_id)
        if not task or task.organization_id != organization_id:
            return False
        if task.status in ("completed", "failed", "cancelled"):
            return False
        task.status = "cancelled"
        task.completed_at = datetime.utcnow()
        self.db.commit()
        return True
