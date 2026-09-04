"""Audit logging for AI Business Assistant governance."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str = ""
    request_id: str = ""
    user_id: str | None = None
    organization_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditLogger:
    """Logs all AI assistant actions for governance and audit trails."""

    def __init__(self, max_entries: int = 10000) -> None:
        self._entries: list[AuditEntry] = []
        self._max_entries = max_entries

    def log_request(
        self, request_id: str, query: str, user_id: str | None, org_id: str | None
    ) -> None:
        self._add_entry(
            AuditEntry(
                action="request_received",
                request_id=request_id,
                user_id=user_id,
                organization_id=org_id,
                details={"query_preview": query[:200], "query_length": len(query)},
            )
        )

    def log_intent(self, request_id: str, intent_detection: Any) -> None:
        self._add_entry(
            AuditEntry(
                action="intent_detected",
                request_id=request_id,
                details={
                    "intent": getattr(intent_detection, "intent", None),
                    "confidence": getattr(intent_detection, "confidence", None),
                    "suggested_tools": getattr(intent_detection, "suggested_tools", []),
                },
            )
        )

    def log_plan(self, request_id: str, plan: Any) -> None:
        self._add_entry(
            AuditEntry(
                action="plan_created",
                request_id=request_id,
                details={
                    "plan_id": getattr(plan, "plan_id", None),
                    "num_steps": len(getattr(plan, "steps", [])),
                    "estimated_time": getattr(plan, "estimated_time", None),
                },
            )
        )

    def log_tool_execution(
        self, request_id: str, tool_name: str, success: bool, execution_time: float
    ) -> None:
        self._add_entry(
            AuditEntry(
                action="tool_executed",
                request_id=request_id,
                details={
                    "tool_name": tool_name,
                    "success": success,
                    "execution_time_ms": round(execution_time * 1000, 2),
                },
            )
        )

    def log_completion(self, request_id: str, total_time: float, num_tools: int) -> None:
        self._add_entry(
            AuditEntry(
                action="request_completed",
                request_id=request_id,
                details={
                    "total_time_ms": round(total_time * 1000, 2),
                    "num_tools_executed": num_tools,
                },
            )
        )

    def log_governance_event(self, event_type: str, details: dict[str, Any]) -> None:
        self._add_entry(
            AuditEntry(
                action=f"governance_{event_type}",
                details=details,
            )
        )

    def log_prompt_version(
        self, prompt_id: str, version: int, approved: bool, approved_by: str | None
    ) -> None:
        self._add_entry(
            AuditEntry(
                action="prompt_version_logged",
                details={
                    "prompt_id": prompt_id,
                    "version": version,
                    "approved": approved,
                    "approved_by": approved_by,
                },
            )
        )

    def get_entries(self, limit: int = 100) -> list[AuditEntry]:
        return self._entries[-limit:]

    def get_entries_by_request(self, request_id: str) -> list[AuditEntry]:
        return [e for e in self._entries if e.request_id == request_id]

    def get_entries_by_user(self, user_id: str) -> list[AuditEntry]:
        return [e for e in self._entries if e.user_id == user_id]

    def _add_entry(self, entry: AuditEntry) -> None:
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]

    def export_audit_log(self, format: str = "json") -> str:
        data = [e.dict() for e in self._entries]
        if format == "json":
            return json.dumps(data, default=str, indent=2)
        return str(data)
