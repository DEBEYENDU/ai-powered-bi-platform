"""AI service — thin wrapper around the provider registry for agent use."""

from __future__ import annotations


async def call_llm(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> str:
    """Call the configured LLM provider. Returns empty string on failure."""
    try:
        from app.ai.providers.registry import get_provider

        llm = get_provider()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        raw = await llm.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
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
        return ""


async def get_agent_capabilities_description() -> str:
    """Return a human-readable description of all registered agents."""
    from app.ai.agents.registry.agent_registry import get_registry

    registry = get_registry()
    lines: list[str] = []
    for info in registry.list_all():
        lines.append(f"- {info['name']} ({info['agent_type']}): status={info['status']}")
    return "\n".join(lines) if lines else "No agents registered"
