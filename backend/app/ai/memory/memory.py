"""Conversation memory system for AI Business Assistant."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.ai.schemas.chat import ChatMessage


class MemoryType:
    SESSION = "session"
    LONG_TERM = "long_term"
    BUSINESS_CONTEXT = "business_context"
    USER_PREFERENCES = "user_preferences"
    RECENT_QUERIES = "recent_queries"
    PINNED_CONTEXT = "pinned_context"


class MemoryEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid4()))
    memory_type: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    relevance_score: float = 0.5

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class ConversationMemory:
    """Manages conversation memory for the AI assistant."""

    MAX_SESSION_HISTORY = 50
    MAX_RECENT_QUERIES = 100
    MAX_LONG_TERM_ENTRIES = 500
    SESSION_TTL_HOURS = 24
    LONG_TERM_TTL_DAYS = 30
    RECENT_QUERY_TTL_DAYS = 7

    def __init__(self) -> None:
        self._session_history: list[ChatMessage] = []
        self._long_term_memory: list[MemoryEntry] = []
        self._business_contexts: dict[str, MemoryEntry] = {}
        self._user_preferences: dict[str, dict[str, Any]] = {}
        self._recent_queries: list[MemoryEntry] = []
        self._pinned_contexts: list[MemoryEntry] = []

    def add_message(
        self, role: str, content: str, metadata: dict[str, Any] | None = None
    ) -> ChatMessage:
        message = ChatMessage(
            role=role,
            content=content,
            metadata=metadata,
        )
        self._session_history.append(message)
        if len(self._session_history) > self.SESSION_TTL_HOURS * 4:
            self._session_history = self._session_history[-self.MAX_SESSION_HISTORY :]
        return message

    def get_session_history(self, limit: int = 20) -> list[ChatMessage]:
        return self._session_history[-limit:]

    def clear_session(self) -> None:
        self._session_history.clear()

    def add_long_term_memory(
        self, content: str, metadata: dict[str, Any] | None = None, ttl_days: int = 30
    ) -> MemoryEntry:
        entry = MemoryEntry(
            memory_type=MemoryType.LONG_TERM,
            content=content,
            metadata=metadata or {},
            expires_at=datetime.utcnow() + timedelta(days=ttl_days),
            relevance_score=0.5,
        )
        self._long_term_memory.append(entry)
        if len(self._long_term_memory) > self.MAX_LONG_TERM_ENTRIES:
            self._long_term_memory = self._long_term_memory[-self.MAX_LONG_TERM_ENTRIES :]
        return entry

    def get_long_term_memory(self, query: str | None = None, limit: int = 10) -> list[MemoryEntry]:
        entries = [e for e in self._long_term_memory if not e.is_expired]
        if query:
            entries = sorted(
                entries,
                key=lambda e: self._relevance_score(e, query),
                reverse=True,
            )
        return entries[:limit]

    def add_business_context(
        self, key: str, content: str, org_id: str | None = None
    ) -> MemoryEntry:
        entry = MemoryEntry(
            memory_type=MemoryType.BUSINESS_CONTEXT,
            content=content,
            metadata={"key": key, "org_id": org_id},
            relevance_score=0.9,
        )
        self._business_contexts[key] = entry
        return entry

    def get_business_context(self, key: str) -> MemoryEntry | None:
        entry = self._business_contexts.get(key)
        if entry and not entry.is_expired:
            return entry
        return None

    def set_user_preference(self, user_id: str, key: str, value: Any) -> None:
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = {}
        self._user_preferences[user_id][key] = value

    def get_user_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        return self._user_preferences.get(user_id, {}).get(key, default)

    def add_recent_query(
        self, query: str, user_id: str | None = None, metadata: dict[str, Any] | None = None
    ) -> MemoryEntry:
        entry = MemoryEntry(
            memory_type=MemoryType.RECENT_QUERIES,
            content=query,
            metadata=metadata or {},
            expires_at=datetime.utcnow() + timedelta(days=self.RECENT_QUERY_TTL_DAYS),
            relevance_score=0.7,
        )
        self._recent_queries.append(entry)
        if len(self._recent_queries) > self.MAX_RECENT_QUERIES:
            self._recent_queries = self._recent_queries[-self.MAX_RECENT_QUERIES :]
        return entry

    def get_recent_queries(self, limit: int = 10) -> list[str]:
        entries = [e for e in self._recent_queries if not e.is_expired]
        return [e.content for e in entries[-limit:]]

    def pin_context(self, content: str, description: str = "") -> MemoryEntry:
        entry = MemoryEntry(
            memory_type=MemoryType.PINNED_CONTEXT,
            content=content,
            metadata={"description": description},
            relevance_score=1.0,
        )
        self._pinned_contexts.append(entry)
        return entry

    def get_pinned_contexts(self) -> list[str]:
        return [e.content for e in self._pinned_contexts if not e.is_expired]

    def summarize_session(self) -> str:
        if not self._session_history:
            return ""
        user_msgs = [m.content for m in self._session_history if m.role == "user"]
        assistant_msgs = [m.content for m in self._session_history if m.role == "assistant"]
        summary = f"Session had {len(user_msgs)} user messages and {len(assistant_msgs)} assistant responses."
        if user_msgs:
            summary += f" Latest query: {user_msgs[-1][:100]}"
        return summary

    def cleanup_expired(self) -> dict[str, int]:
        cleaned: dict[str, int] = {}
        before = len(self._long_term_memory)
        self._long_term_memory = [e for e in self._long_term_memory if not e.is_expired]
        cleaned["long_term"] = before - len(self._long_term_memory)
        before = len(self._recent_queries)
        self._recent_queries = [e for e in self._recent_queries if not e.is_expired]
        cleaned["recent_queries"] = before - len(self._recent_queries)
        return cleaned

    def get_context_for_query(self, query: str) -> dict[str, list[str]]:
        context: dict[str, list[str]] = {
            "pinned": self.get_pinned_contexts(),
            "long_term": [e.content for e in self.get_long_term_memory(query, limit=5)],
            "session": [m.content for m in self.get_session_history(limit=10)],
        }
        return context

    def _relevance_score(self, entry: MemoryEntry, query: str) -> float:
        query_lower = query.lower()
        content_lower = entry.content.lower()
        score = entry.relevance_score
        if query_lower in content_lower or content_lower in query_lower:
            score += 0.3
        for word in query_lower.split():
            if len(word) > 3 and word in content_lower:
                score += 0.05
        return min(1.0, score)
