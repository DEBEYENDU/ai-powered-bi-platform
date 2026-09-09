"""Provider registry - resolves provider name to instance."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings


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


def list_providers() -> list[dict[str, Any]]:
    """Return metadata about all available providers."""
    return [
        {"id": "openai", "name": "OpenAI", "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]},
        {"id": "ollama", "name": "Ollama (Local)", "models": ["llama3", "mistral", "codellama"]},
        {"id": "lmstudio", "name": "LM Studio (Local)", "models": ["local-model"]},
        {"id": "azure", "name": "Azure OpenAI", "models": ["gpt-4o", "gpt-4o-mini"]},
        {"id": "gemini", "name": "Google Gemini", "models": ["gemini-1.5-flash", "gemini-1.5-pro"]},
        {"id": "anthropic", "name": "Anthropic Claude", "models": ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"]},
    ]
