"""Chat schemas for the AI assistant."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    conversation_id: str | None = Field(None, description="Existing conversation ID")
    model: str | None = Field(None, description="Model override")
    provider: str | None = Field(None, description="Provider override")
    temperature: float = Field(0.7, ge=0, le=2)
    max_tokens: int = Field(4096, ge=1, le=128000)
    system_prompt: str | None = Field(None, description="Custom system prompt")
    stream: bool = Field(True, description="Enable SSE streaming")


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    message_id: str
    model: str
    provider: str
    token_count: int = 0
    finish_reason: str | None = None


class StreamChunk(BaseModel):
    """A single SSE streaming chunk."""

    delta: str = ""
    conversation_id: str = ""
    message_id: str = ""
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None


class ConversationOut(BaseModel):
    id: str
    title: str
    model: str
    provider: str
    message_count: int
    total_tokens: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationOut):
    messages: list[ConversationMessageOut] = []


class ConversationMessageOut(BaseModel):
    id: str
    role: str
    content: str
    token_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationUpdate(BaseModel):
    title: str | None = None
    model: str | None = None
    provider: str | None = None
    system_prompt: str | None = None


class ProviderOut(BaseModel):
    id: str
    name: str
    models: list[str]


class AIHealthOut(BaseModel):
    status: str
    providers: list[dict[str, Any]]
    active_provider: str
    active_model: str


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
