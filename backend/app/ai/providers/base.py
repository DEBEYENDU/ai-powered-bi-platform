"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatChunk:
    """A single streaming chunk."""

    delta: str
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None


@dataclass
class LLMResponse:
    """Full non-streaming response."""

    content: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)
    finish_reason: str | None = None


class LLMProvider(ABC):
    """Abstract base for all LLM providers."""

    name: str = "base"

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a chat completion request (non-streaming)."""

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[ChatChunk]:
        """Send a chat completion request (streaming)."""

    def list_models(self) -> list[str]:
        """Return available models for this provider."""
        return []

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the provider is reachable."""
