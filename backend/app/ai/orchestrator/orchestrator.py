"""Main AI Orchestrator - coordinates intent detection, planning, tool execution, and response generation."""

from __future__ import annotations

import asyncio
import time
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.ai.cache.caching import AICache
from app.ai.citations.citation_engine import CitationEngine
from app.ai.governance.audit import AuditLogger
from app.ai.governance.hallucination import HallucinationDetector
from app.ai.moderation.safety import SafetyChecker
from app.ai.orchestrator.intent_detector import IntentDetection, IntentDetector
from app.ai.orchestrator.planner import ExecutionPlan, Planner, PlanStep
from app.ai.tools.registry import ToolRegistry


class ToolExecutionResult(BaseModel):
    tool_name: str
    success: bool
    data: Any | None = None
    error: str | None = None
    execution_time: float = 0.0
    cached: bool = False


class Orchestrator(BaseModel):
    intent_detector: IntentDetector = Field(default_factory=IntentDetector)
    planner: Planner = Field(default_factory=Planner)
    registry: ToolRegistry | None = None
    cache: AICache | None = None
    safety_checker: SafetyChecker | None = None
    audit_logger: AuditLogger | None = None
    hallucination_detector: HallucinationDetector | None = None
    citation_engine: CitationEngine | None = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        if self.registry is None:
            self.registry = ToolRegistry()
        if self.cache is None:
            self.cache = AICache()
        if self.safety_checker is None:
            self.safety_checker = SafetyChecker()
        if self.audit_logger is None:
            self.audit_logger = AuditLogger()
        if self.hallucination_detector is None:
            self.hallucination_detector = HallucinationDetector()
        if self.citation_engine is None:
            self.citation_engine = CitationEngine()
        self._execution_results: dict[str, ToolExecutionResult] = {}

    async def process_query(
        self,
        query: str,
        user_id: str | None = None,
        organization_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        start_time = time.time()
        request_id = str(uuid4())

        self.audit_logger.log_request(request_id, query, user_id, organization_id)

        query_text = self.safety_checker.sanitize_input(query)
        has_safety_issue = not self.safety_checker.is_safe(query_text)

        if has_safety_issue:
            return self._build_safety_response(request_id, query_text, time.time() - start_time)

        intent_detection = self.intent_detector.detect(query_text, context)
        self.audit_logger.log_intent(request_id, intent_detection)

        if intent_detection.needs_human_review:
            return self._build_human_review_response(
                request_id, intent_detection, time.time() - start_time
            )

        plan = self.planner.create_plan(intent_detection, self.registry.list_tools(), context)
        self.audit_logger.log_plan(request_id, plan)

        execution_results = await self._execute_plan(
            plan, request_id, user_id, organization_id, context
        )

        self._execution_results = {r.tool_name: r for r in execution_results}

        self.hallucination_detector.validate(execution_results)

        citations = await self.citation_engine.generate(execution_results, request_id)

        response_text = await self._generate_response(
            intent_detection, execution_results, citations
        )

        suggested_questions = self._suggest_follow_up(intent_detection, execution_results)

        total_time = time.time() - start_time
        self.audit_logger.log_completion(request_id, total_time, len(execution_results))

        return {
            "request_id": request_id,
            "query": query_text,
            "intent": intent_detection.intent,
            "confidence": intent_detection.confidence,
            "response": response_text,
            "citations": citations,
            "execution_results": [r.dict() for r in execution_results],
            "suggested_questions": suggested_questions,
            "execution_time_ms": round(total_time * 1000, 2),
        }

    async def _execute_plan(
        self,
        plan: ExecutionPlan,
        request_id: str,
        user_id: str | None,
        organization_id: str | None,
        context: dict[str, Any] | None,
    ) -> list[ToolExecutionResult]:
        parallel_groups = plan.get_parallel_groups()
        results: list[ToolExecutionResult] = []

        if parallel_groups:
            tasks = []
            for group_name, steps in parallel_groups.items():
                tasks.append(
                    self._execute_step_group(
                        group_name, steps, request_id, user_id, organization_id, context
                    )
                )
            group_results = await asyncio.gather(*tasks, return_exceptions=True)
            for group_result in group_results:
                if isinstance(group_result, Exception):
                    continue
                results.extend(group_result)
        else:
            ordered_steps = plan.get_ordered_steps()
            for step in ordered_steps:
                result = await self._execute_single_step(
                    step, request_id, user_id, organization_id, context
                )
                results.append(result)

        return results

    async def _execute_step_group(
        self,
        group_name: str,
        steps: list[PlanStep],
        request_id: str,
        user_id: str | None,
        organization_id: str | None,
        context: dict[str, Any] | None,
    ) -> list[ToolExecutionResult]:
        tasks = [
            self._execute_single_step(step, request_id, user_id, organization_id, context)
            for step in steps
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_single_step(
        self,
        step: PlanStep,
        request_id: str,
        user_id: str | None,
        organization_id: str | None,
        context: dict[str, Any] | None,
    ) -> ToolExecutionResult:
        tool_def = self.registry.get(step.tool_name)
        if tool_def is None:
            return ToolExecutionResult(
                tool_name=step.tool_name,
                success=False,
                error=f"Tool '{step.tool_name}' not registered",
                execution_time=0.0,
            )
        start = time.time()
        try:
            instance = self.registry.get_instance(step.tool_name)
            handler = instance.execute if instance is not None else tool_def.handler
            result_data = handler(context=context, step=step)
            if asyncio.iscoroutine(result_data):
                data = await result_data
            else:
                data = result_data
            elapsed = time.time() - start
            return ToolExecutionResult(
                tool_name=step.tool_name,
                success=True,
                data=data,
                execution_time=elapsed,
            )
        except TimeoutError:
            elapsed = time.time() - start
            return ToolExecutionResult(
                tool_name=step.tool_name,
                success=False,
                error=f"Tool timed out after {step.timeout}s",
                execution_time=elapsed,
            )
        except Exception as e:
            elapsed = time.time() - start
            return ToolExecutionResult(
                tool_name=step.tool_name,
                success=False,
                error=str(e),
                execution_time=elapsed,
            )

    async def _generate_response(
        self,
        intent: IntentDetection,
        results: list[ToolExecutionResult],
        citations: list[Any],
    ) -> str:
        successful = [r for r in results if r.success]
        if not successful:
            return self._build_fallback_response(intent)
        summary_parts = []
        for r in successful:
            summary_parts.append(self._format_result(r))
        return " ".join(summary_parts)

    def _format_result(self, result: ToolExecutionResult) -> str:
        if result.data is None:
            return f"Tool {result.tool_name} completed without data."
        if isinstance(result.data, dict):
            if "summary" in result.data:
                return result.data["summary"]
            return str(result.data)
        return str(result.data)

    def _build_safety_response(self, request_id: str, query: str, elapsed: float) -> dict[str, Any]:
        return {
            "request_id": request_id,
            "query": query,
            "response": "I'm unable to process this request. It may contain inappropriate content.",
            "citations": [],
            "suggested_questions": [],
            "execution_time_ms": round(elapsed * 1000, 2),
        }

    def _build_human_review_response(
        self, request_id: str, intent: IntentDetection, elapsed: float
    ) -> dict[str, Any]:
        return {
            "request_id": request_id,
            "intent": intent.intent,
            "response": "This query requires human review for accuracy.",
            "citations": [],
            "suggested_questions": [],
            "execution_time_ms": round(elapsed * 1000, 2),
        }

    def _build_fallback_response(self, intent: IntentDetection) -> str:
        return f"I processed your query about '{intent.intent}'. I couldn't retrieve specific data. Please try rephrasing or ask a more specific question."

    def _suggest_follow_up(
        self, intent: IntentDetection, results: list[ToolExecutionResult]
    ) -> list[str]:
        suggestions = [
            "Can you provide more details about this?",
            "Would you like to see this in a chart?",
            "Would you like to compare with another period?",
            "Would you like a deeper analysis?",
        ]
        return suggestions[:3]

    def get_execution_summary(self) -> dict[str, Any]:
        total = len(self._execution_results)
        successful = sum(1 for r in self._execution_results.values() if r.success)
        return {"total_tools": total, "successful": successful, "failed": total - successful}
