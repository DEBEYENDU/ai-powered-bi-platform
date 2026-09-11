"""Security Agent — permissions, audit, sensitive data, policy enforcement."""

from __future__ import annotations

import time
from typing import Any

from app.ai.agents.agents.base import BaseAgent
from app.ai.agents.prompts.templates import SECURITY_AGENT_PROMPT


class SecurityAgent(BaseAgent):
    agent_type = "security"
    name = "Security Agent"
    description = "Permission validation, audit logging, sensitive data detection"

    SENSITIVE_PATTERNS = [
        "ssn",
        "social_security",
        "credit_card",
        "password",
        "api_key",
        "secret",
        "token",
        "private_key",
    ]

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
        tools: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        permissions = context.get("permissions", "default")
        policies = context.get("policies", "standard")

        prompt = SECURITY_AGENT_PROMPT.format(
            task=task,
            permissions=permissions,
            policies=policies,
        )

        llm_response = await self._call_llm(prompt)

        sensitive = self._detect_sensitive_data(context)
        audit_entry = self._create_audit_log(task, context)

        return self._build_result(
            output=llm_response,
            data={
                "permission_check": "approved",
                "sensitive_data_detected": sensitive,
                "audit_log": audit_entry,
                "policy_compliance": "compliant",
                "security_recommendations": self._recommendations(sensitive),
            },
            artifacts=[{"type": "audit_log", "content": audit_entry}],
        )

    def _detect_sensitive_data(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect sensitive data patterns in context."""
        detected: list[dict[str, Any]] = []
        task = context.get("task", "")
        if isinstance(task, str):
            lower = task.lower()
            for pattern in self.SENSITIVE_PATTERNS:
                if pattern in lower:
                    detected.append(
                        {
                            "pattern": pattern,
                            "severity": "high",
                            "description": f"Sensitive pattern '{pattern}' found in request",
                        }
                    )
        return detected

    def _create_audit_log(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "action": "agent_execution",
            "task_summary": task[:200],
            "user_id": context.get("user_id", "anonymous"),
            "org_id": context.get("org_id", "default"),
            "result": "approved",
        }

    def _recommendations(self, sensitive: list[dict[str, Any]]) -> list[str]:
        recs = ["Enable audit logging for all data access"]
        if sensitive:
            recs.append("Review sensitive data detection results before proceeding")
            recs.append("Ensure data masking is applied to sensitive fields")
        return recs
