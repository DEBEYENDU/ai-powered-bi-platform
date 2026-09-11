"""Base agent class — all agents inherit from this."""

from __future__ import annotations

from typing import Any


class BaseAgent:
    """Base class for all agents. Provides common interface and helpers."""

    agent_type: str = "base"
    name: str = "Base Agent"
    description: str = ""

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
        tools: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute the agent's task. Must be overridden by subclasses."""
        raise NotImplementedError

    def _build_result(
        self,
        output: str,
        data: dict[str, Any] | None = None,
        artifacts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Build a standardized result dict."""
        return {
            "agent_type": self.agent_type,
            "output": output,
            "data": data or {},
            "artifacts": artifacts or [],
        }

    async def _call_llm(self, prompt: str, system_prompt: str = "", **kwargs: Any) -> str:
        """Call the LLM provider. Falls back to echo if unavailable."""
        try:
            from app.ai.providers.registry import get_provider

            llm = get_provider()
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            raw = await llm.chat_completion(
                messages=messages,
                temperature=kwargs.get("temperature", 0.3),
                max_tokens=kwargs.get("max_tokens", 2000),
            )
            # Extract text from various response formats
            if isinstance(raw, str):
                return raw
            if isinstance(raw, dict):
                if raw.get("choices"):
                    return raw["choices"][0].get("message", {}).get("content", str(raw))
                return str(raw)
            if hasattr(raw, "choices") and raw.choices:
                return raw.choices[0].message.content or ""
            return str(raw)
        except Exception:
            return f"[{self.name}] LLM unavailable — using rule-based fallback"
