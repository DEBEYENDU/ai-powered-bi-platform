"""Azure OpenAI provider."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.ai.providers.base import ChatChunk, ChatMessage, LLMProvider, LLMResponse


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI using the /deployments/{deployment} API."""

    name = "azure"

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        api_version: str = "2024-02-01",
        deployment: str = "",
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.api_version = api_version
        self.deployment = deployment
        self.timeout = timeout

    def _url(self, model: str) -> str:
        deployment = self.deployment or model
        return (
            f"{self.base_url}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={self.api_version}"
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        payload = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(self._url(model), headers=self._headers(), json=payload)
            r.raise_for_status()
            data = r.json()
        choice = data["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", model),
            usage=data.get("usage", {}),
            finish_reason=choice.get("finish_reason"),
        )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[ChatChunk]:
        payload = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client, client.stream(
            "POST", self._url(model), headers=self._headers(), json=payload
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                chunk_str = line[6:]
                if chunk_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(chunk_str)
                except json.JSONDecodeError:
                    continue
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield ChatChunk(
                        delta=content,
                        finish_reason=chunk["choices"][0].get("finish_reason"),
                    )

    def list_models(self) -> list[str]:
        return ["gpt-4o", "gpt-4o-mini", "gpt-4"]

    def health_check(self) -> bool:
        try:
            r = httpx.get(
                f"{self.base_url}/openai/models?api-version={self.api_version}",
                headers=self._headers(),
                timeout=5.0,
            )
            return r.status_code == 200
        except Exception:  # noqa: BLE001
            return False
