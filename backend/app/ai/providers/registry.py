"""Provider registry - resolves provider name to instance."""

from __future__ import annotations

import time
from typing import Any

from app.core.config import get_settings

_DEFAULT_FALLBACK_MODELS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    "ollama": ["llama3", "mistral", "codellama"],
    "lmstudio": ["local-model"],
    "azure": ["gpt-4o", "gpt-4o-mini"],
    "gemini": ["gemini-1.5-flash", "gemini-1.5-pro"],
    "anthropic": ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"],
}

# model-list cache: (timestamp, models). Remote /models calls are cached so the
# providers endpoint never blocks on a slow provider.
_MODEL_CACHE: dict[str, tuple[float, list[str]]] = {}
_CACHE_TTL_SECONDS = 60.0


def get_provider(name: str | None = None) -> Any:
    """Get a provider instance by name. Falls back to configured default."""
    settings = get_settings()
    provider_name = name or getattr(settings, "ai_provider", "openai")

    if provider_name == "ollama":
        from app.ai.providers.ollama_provider import OllamaProvider

        return OllamaProvider(
            base_url=getattr(settings, "ollama_base_url", "http://localhost:11434"),
        )

    if provider_name == "lmstudio":
        from app.ai.providers.lmstudio_provider import LMStudioProvider

        return LMStudioProvider(
            base_url=getattr(settings, "lmstudio_base_url", "http://localhost:1234/v1"),
        )

    if provider_name == "azure":
        from app.ai.providers.azure_provider import AzureOpenAIProvider

        return AzureOpenAIProvider(
            api_key=getattr(settings, "azure_openai_api_key", ""),
            base_url=getattr(settings, "azure_openai_endpoint", ""),
            api_version=getattr(settings, "azure_openai_api_version", "2024-02-01"),
            deployment=getattr(settings, "azure_openai_deployment", ""),
        )

    if provider_name == "gemini":
        from app.ai.providers.gemini_provider import GeminiProvider

        return GeminiProvider(
            api_key=getattr(settings, "gemini_api_key", ""),
        )

    if provider_name == "anthropic":
        from app.ai.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            api_key=getattr(settings, "anthropic_api_key", ""),
        )

    # Default: OpenAI (also covers any OpenAI-compatible endpoint)
    from app.ai.providers.openai_provider import OpenAIProvider

    return OpenAIProvider(
        api_key=getattr(settings, "openai_api_key", ""),
        base_url=getattr(settings, "openai_base_url", "https://api.openai.com/v1"),
    )


def _cached(key: str, fetch: Any) -> tuple[list[str], bool]:
    """Return (models, reachable), caching successful/unsuccessful probes."""
    now = time.monotonic()
    hit = _MODEL_CACHE.get(key)
    if hit and now - hit[0] < _CACHE_TTL_SECONDS:
        return hit[1]
    try:
        value = fetch()
    except Exception:  # noqa: BLE001
        value = ([], False)
    _MODEL_CACHE[key] = (now, value)
    return value


def _probe_openai(settings: Any) -> tuple[list[str], bool]:
    import httpx

    base_url = getattr(settings, "openai_base_url", "https://api.openai.com/v1").rstrip("/")
    api_key = getattr(settings, "openai_api_key", "")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    r = httpx.get(f"{base_url}/models", headers=headers, timeout=4.0)
    r.raise_for_status()
    data = r.json()
    models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
    return models, True


def _probe_ollama(settings: Any) -> tuple[list[str], bool]:
    import httpx

    base_url = getattr(settings, "ollama_base_url", "http://localhost:11434").rstrip("/")
    r = httpx.get(f"{base_url}/api/tags", timeout=4.0)
    r.raise_for_status()
    data = r.json()
    models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    return models, True


def _ordered(models: list[str], default_model: str, limit: int = 60) -> list[str]:
    """Put the configured default model first, de-duplicate, cap the list."""
    seen: list[str] = []
    if default_model:
        seen.append(default_model)
    for m in models:
        if m and m not in seen:
            seen.append(m)
        if len(seen) >= limit:
            break
    return seen


def list_providers() -> list[dict[str, Any]]:
    """Return metadata about all available providers.

    Model lists for the configured OpenAI-compatible endpoint and for Ollama are
    probed live (cached for 60s) so the UI never offers a model the backend
    cannot actually call. Providers without live discovery keep their static
    list and are reported with ``available: false`` when unconfigured.
    """
    settings = get_settings()
    default_provider = getattr(settings, "ai_provider", "openai")
    default_model = getattr(settings, "ai_model", "")

    # OpenAI-compatible (configured base URL may be OpenAI, NVIDIA NIM, LM Studio...)
    openai_models, openai_ok = _cached("openai", lambda: _probe_openai(settings))
    # Ollama local server
    ollama_models, ollama_ok = _cached("ollama", lambda: _probe_ollama(settings))

    spec: dict[str, dict[str, Any]] = {
        "openai": {
            "name": "OpenAI",
            "models": list(openai_models),
            "available": openai_ok,
        },
        "ollama": {
            "name": "Ollama (Local)",
            "models": list(ollama_models),
            "available": ollama_ok and bool(ollama_models),
        },
        "lmstudio": {
            "name": "LM Studio (Local)",
            "models": _DEFAULT_FALLBACK_MODELS["lmstudio"],
            "available": False,
        },
        "azure": {
            "name": "Azure OpenAI",
            "models": _DEFAULT_FALLBACK_MODELS["azure"],
            "available": bool(getattr(settings, "azure_openai_api_key", "")),
        },
        "gemini": {
            "name": "Google Gemini",
            "models": _DEFAULT_FALLBACK_MODELS["gemini"],
            "available": bool(getattr(settings, "gemini_api_key", "")),
        },
        "anthropic": {
            "name": "Anthropic Claude",
            "models": _DEFAULT_FALLBACK_MODELS["anthropic"],
            "available": bool(getattr(settings, "anthropic_api_key", "")),
        },
    }

    order = [default_provider, *[pid for pid in spec if pid != default_provider]]
    entries: list[dict[str, Any]] = []
    for pid in order:
        meta = spec.get(pid)
        if meta is None:
            continue
        models = list(meta["models"])
        if pid == default_provider and default_model:
            # The configured model always comes first for the active provider.
            models = _ordered(models, default_model)
        if not models:
            models = list(_DEFAULT_FALLBACK_MODELS.get(pid, []))
        entries.append(
            {
                "id": pid,
                "name": meta["name"],
                "models": models,
                "available": meta["available"],
                "configured": pid == default_provider,
                "default_model": default_model,
            }
        )
    return entries
