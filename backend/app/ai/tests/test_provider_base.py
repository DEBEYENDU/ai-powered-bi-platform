"""Provider adapter tests.

Every AI service calls ``llm.chat_completion(messages=[...])`` while providers
only implement ``chat``/``chat_stream`` — the adapter on ``LLMProvider`` is
what keeps those 16 call sites from raising ``AttributeError`` and silently
degrading to "AI unavailable" text.
"""

from __future__ import annotations

from app.ai.providers.base import ChatChunk, ChatMessage, LLMProvider, LLMResponse
from app.core.config import get_settings


class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def chat(self, messages, model, temperature=0.7, max_tokens=4096, **kwargs):
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return LLMResponse(content="provider answer", model=model, usage={"prompt_tokens": 3})

    async def chat_stream(self, messages, model, temperature=0.7, max_tokens=4096, **kwargs):
        yield ChatChunk(delta="streamed")

    def health_check(self) -> bool:
        return True


class TestChatCompletionAdapter:
    async def test_returns_provider_text(self):
        provider = FakeProvider()
        out = await provider.chat_completion([{"role": "user", "content": "hi"}])
        assert out == "provider answer"
        assert len(provider.calls) == 1

    async def test_converts_dict_messages_to_chat_messages(self):
        provider = FakeProvider()
        await provider.chat_completion(
            [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "q"},
                ChatMessage(role="assistant", content="a"),
            ]
        )
        messages = provider.calls[0]["messages"]
        assert all(isinstance(m, ChatMessage) for m in messages)
        assert [m.role for m in messages] == ["system", "user", "assistant"]
        assert [m.content for m in messages] == ["sys", "q", "a"]

    async def test_uses_configured_default_model_and_forwards_kwargs(self):
        provider = FakeProvider()
        await provider.chat_completion(
            [{"role": "user", "content": "q"}], temperature=0.1, max_tokens=42
        )
        call = provider.calls[0]
        assert call["model"] == get_settings().ai_model
        assert call["temperature"] == 0.1
        assert call["max_tokens"] == 42

    async def test_explicit_model_wins(self):
        provider = FakeProvider()
        await provider.chat_completion([{"role": "user", "content": "q"}], model="m1")
        assert provider.calls[0]["model"] == "m1"
