"""Google Gemini provider."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.ai.providers.base import ChatChunk, ChatMessage, LLMProvider, LLMResponse


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    name = "gemini"

    def __init__(self, api_key: str = "", timeout: float = 120.0) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def _convert_messages(
        self, messages: list[ChatMessage]
    ) -> tuple[str, list[dict[str, Any]]]:
        """Convert to Gemini format: system instruction + contents."""
        system = ""
        contents: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                role = "user" if m.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": m.content}]})
        return system, contents

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        system, contents = self._convert_messages(messages)
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        candidates = data.get("candidates", [])
        content = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)
        usage_meta = data.get("usageMetadata", {})
        return LLMResponse(
            content=content,
            model=model,
            usage={
                "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
            },
            finish_reason="stop",
        )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[ChatChunk]:
        system, contents = self._convert_messages(messages)
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        url = f"{self.base_url}/models/{model}:streamGenerateContent?key={self.api_key}&alt=sse"
        async with httpx.AsyncClient(timeout=self.timeout) as client:  # noqa: SIM117
            async with client.stream("POST", url, json=payload) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    import json

                    try:
                        chunk = json.loads(line[6:])
                    except (json.JSONDecodeError, ValueError):
                        continue
                    candidates = chunk.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts)
                        if text:
                            yield ChatChunk(delta=text, finish_reason=None)

    def list_models(self) -> list[str]:
        return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]

    def health_check(self) -> bool:
        try:
            r = httpx.get(
                f"{self.base_url}/models?key={self.api_key}",
                timeout=5.0,
            )
            return r.status_code == 200
        except Exception:  # noqa: BLE001
            return False
