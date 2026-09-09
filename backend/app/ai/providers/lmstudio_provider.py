"""LM Studio provider (OpenAI-compatible local server)."""

from __future__ import annotations

from app.ai.providers.openai_provider import OpenAIProvider


class LMStudioProvider(OpenAIProvider):
    """LM Studio uses the OpenAI-compatible API on localhost:1234."""

    name = "lmstudio"

    def __init__(self, base_url: str = "http://localhost:1234/v1", **kwargs) -> None:
        super().__init__(base_url=base_url, api_key="lm-studio", **kwargs)

    def list_models(self) -> list[str]:
        try:
            return super().list_models()
        except Exception:  # noqa: BLE001
            return ["local-model"]
