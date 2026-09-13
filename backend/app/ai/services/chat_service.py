"""Chat service - manages conversations and interfaces with LLM providers."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.models.conversation import Conversation
from app.ai.models.message import Message
from app.ai.providers.base import ChatChunk, ChatMessage
from app.ai.providers.registry import get_provider
from app.core.config import get_settings

SYSTEM_PROMPT_DEFAULT = (
    "You are an AI Business Intelligence assistant. "
    "You help users understand their business data, KPIs, analytics, and dashboards. "
    "You can answer questions about revenue, sales, customers, inventory, and other business metrics. "
    "Format your responses using Markdown for readability: use headings, bullet points, "
    "code blocks, and tables when appropriate. "
    "If you don't have sufficient data to answer a question, be explicit about the limitation."
)


class ChatService:
    """Service for AI chat operations."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def _default_model(self) -> str:
        return getattr(self.settings, "ai_model", "gpt-4o-mini")

    def _default_provider_name(self) -> str:
        return getattr(self.settings, "ai_provider", "openai")

    def _default_temperature(self) -> float:
        return float(getattr(self.settings, "ai_temperature", 0.7))

    def _default_max_tokens(self) -> int:
        return int(getattr(self.settings, "ai_max_tokens", 4096))

    def _system_prompt(self, custom: str | None = None) -> str:
        return custom or SYSTEM_PROMPT_DEFAULT

    def create_conversation(
        self,
        title: str = "New conversation",
        user_id: str | None = None,
        organization_id: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        system_prompt: str | None = None,
    ) -> Conversation:
        conv = Conversation(
            id=str(uuid4()),
            title=title,
            user_id=user_id,
            organization_id=organization_id,
            model=model or self._default_model(),
            provider=provider or self._default_provider_name(),
            system_prompt=system_prompt,
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        return self.db.get(Conversation, conversation_id)

    def list_conversations(
        self,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        stmt = select(Conversation).order_by(Conversation.updated_at.desc())
        if user_id:
            stmt = stmt.where(Conversation.user_id == user_id)
        stmt = stmt.offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count_conversations(self, user_id: str | None = None) -> int:
        stmt = select(func.count()).select_from(Conversation)
        if user_id:
            stmt = stmt.where(Conversation.user_id == user_id)
        return self.db.scalar(stmt) or 0

    def delete_conversation(self, conversation_id: str) -> bool:
        conv = self.get_conversation(conversation_id)
        if not conv:
            return False
        self.db.delete(conv)
        self.db.commit()
        return True

    def update_conversation(
        self,
        conversation_id: str,
        title: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        system_prompt: str | None = None,
    ) -> Conversation | None:
        conv = self.get_conversation(conversation_id)
        if not conv:
            return None
        if title is not None:
            conv.title = title
        if model is not None:
            conv.model = model
        if provider is not None:
            conv.provider = provider
        if system_prompt is not None:
            conv.system_prompt = system_prompt
        conv.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def get_messages(self, conversation_id: str, limit: int = 100) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def _build_history(self, conversation_id: str, max_messages: int = 50) -> list[ChatMessage]:
        """Build LLM message history from DB."""
        conv = self.get_conversation(conversation_id)
        system = self._system_prompt(conv.system_prompt if conv else None)
        messages = [ChatMessage(role="system", content=system)]

        db_messages = self.get_messages(conversation_id, limit=max_messages)
        for msg in db_messages:
            messages.append(ChatMessage(role=msg.role, content=msg.content))
        return messages

    def _save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        token_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        msg = Message(
            id=str(uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            token_count=token_count,
            metadata_=metadata,
        )
        self.db.add(msg)

        conv = self.get_conversation(conversation_id)
        if conv:
            conv.message_count += 1
            conv.total_tokens += token_count
            conv.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(msg)
        return msg

    def _auto_title(self, message: str) -> str:
        """Generate a short title from the first user message."""
        title = message.strip().replace("\n", " ")[:80]
        return title if title else "New conversation"

    async def send_message(
        self,
        conversation_id: str,
        message: str,
        model: str | None = None,
        provider_name: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Send a message and get a non-streaming response."""
        conv = self.get_conversation(conversation_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")

        self._save_message(conversation_id, "user", message)

        if conv.message_count <= 1 and conv.title == "New conversation":
            conv.title = self._auto_title(message)
            self.db.commit()

        history = self._build_history(conversation_id)
        provider = get_provider(provider_name or conv.provider)
        model = model or conv.model
        temp = temperature if temperature is not None else self._default_temperature()
        tokens = max_tokens or self._default_max_tokens()

        if system_prompt:
            history[0] = ChatMessage(role="system", content=self._system_prompt(system_prompt))

        t0 = time.time()
        response = await provider.chat(history, model=model, temperature=temp, max_tokens=tokens)
        elapsed = time.time() - t0

        usage = response.usage
        token_count = usage.get("completion_tokens", 0) + usage.get("prompt_tokens", 0)

        saved = self._save_message(
            conversation_id,
            "assistant",
            response.content,
            token_count=token_count,
            metadata={"model": response.model, "elapsed_s": round(elapsed, 3)},
        )

        return {
            "answer": response.content,
            "conversation_id": conversation_id,
            "message_id": saved.id,
            "model": response.model,
            "provider": provider.name,
            "token_count": token_count,
            "finish_reason": response.finish_reason,
        }

    async def send_message_stream(
        self,
        conversation_id: str,
        message: str,
        model: str | None = None,
        provider_name: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[ChatChunk]:
        """Send a message and stream the response."""
        conv = self.get_conversation(conversation_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")

        self._save_message(conversation_id, "user", message)

        if conv.message_count <= 1 and conv.title == "New conversation":
            conv.title = self._auto_title(message)
            self.db.commit()

        history = self._build_history(conversation_id)
        provider = get_provider(provider_name or conv.provider)
        model = model or conv.model
        temp = temperature if temperature is not None else self._default_temperature()
        tokens = max_tokens or self._default_max_tokens()

        if system_prompt:
            history[0] = ChatMessage(role="system", content=self._system_prompt(system_prompt))

        full_content = ""
        total_tokens = 0
        finish_reason = None

        async for chunk in provider.chat_stream(
            history, model=model, temperature=temp, max_tokens=tokens
        ):
            full_content += chunk.delta
            if chunk.usage:
                total_tokens = chunk.usage.get("completion_tokens", 0) + chunk.usage.get(
                    "prompt_tokens", 0
                )
            if chunk.finish_reason:
                finish_reason = chunk.finish_reason
            yield chunk

        saved = self._save_message(
            conversation_id,
            "assistant",
            full_content,
            token_count=total_tokens,
            metadata={"model": model, "streamed": True},
        )

        yield ChatChunk(
            delta="",
            finish_reason=finish_reason or "stop",
            usage={"message_id": saved.id, "total_tokens": total_tokens},
        )
