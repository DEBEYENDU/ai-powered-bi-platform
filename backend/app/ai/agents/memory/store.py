"""Memory store — conversation, session, task, shared, and vector memory."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import Any


class MemoryStore:
    """In-memory store with optional Redis persistence.

    Implements conversation memory, session memory, task memory,
    shared agent memory, and vector similarity search.
    """

    def __init__(self) -> None:
        self._conversation: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._session: dict[str, dict[str, Any]] = defaultdict(dict)
        self._task: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._shared: dict[str, dict[str, Any]] = defaultdict(dict)
        self._vector: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Conversation memory
    # ------------------------------------------------------------------

    def add_conversation(
        self, session_id: str, role: str, content: str, agent_type: str = ""
    ) -> None:
        entry = {
            "id": str(uuid.uuid4())[:8],
            "role": role,
            "content": content,
            "agent_type": agent_type,
            "timestamp": time.time(),
        }
        self._conversation[session_id].append(entry)

    def get_conversation(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        return self._conversation[session_id][-limit:]

    def clear_conversation(self, session_id: str) -> None:
        self._conversation.pop(session_id, None)

    # ------------------------------------------------------------------
    # Session memory
    # ------------------------------------------------------------------

    def set_session(self, session_id: str, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        self._session[session_id][key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds,
        }

    def get_session(self, session_id: str, key: str) -> Any | None:
        entry = self._session[session_id].get(key)
        if entry and entry["expires_at"] > time.time():
            return entry["value"]
        if entry:
            del self._session[session_id][key]
        return None

    def get_session_all(self, session_id: str) -> dict[str, Any]:
        now = time.time()
        return {
            k: v["value"] for k, v in self._session[session_id].items() if v["expires_at"] > now
        }

    # ------------------------------------------------------------------
    # Task memory
    # ------------------------------------------------------------------

    def add_task_memory(self, task_id: str, agent_type: str, data: dict[str, Any]) -> None:
        entry = {
            "id": str(uuid.uuid4())[:8],
            "agent_type": agent_type,
            "data": data,
            "timestamp": time.time(),
        }
        self._task[task_id].append(entry)

    def get_task_memory(self, task_id: str) -> list[dict[str, Any]]:
        return self._task.get(task_id, [])

    def get_task_context(self, task_id: str, agent_type: str) -> dict[str, Any]:
        """Get aggregated context from all prior agents for this task."""
        context: dict[str, Any] = {}
        for entry in self._task.get(task_id, []):
            if entry["agent_type"] != agent_type:
                context[entry["agent_type"]] = entry["data"]
        return context

    # ------------------------------------------------------------------
    # Shared agent memory
    # ------------------------------------------------------------------

    def set_shared(self, key: str, value: Any, agent_type: str = "") -> None:
        self._shared[key] = {
            "value": value,
            "agent_type": agent_type,
            "updated_at": time.time(),
        }

    def get_shared(self, key: str) -> Any | None:
        entry = self._shared.get(key)
        return entry["value"] if entry else None

    def get_all_shared(self) -> dict[str, Any]:
        return {k: v["value"] for k, v in self._shared.items()}

    # ------------------------------------------------------------------
    # Vector memory (simple cosine similarity)
    # ------------------------------------------------------------------

    def add_vector(
        self,
        key: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._vector[key] = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }

    def search_vector(self, query_embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        if not query_embedding or not self._vector:
            return []

        results: list[tuple[str, float]] = []
        q_norm = query_embedding.copy()

        for key, entry in self._vector.items():
            emb = entry["embedding"]
            sim = _cosine_similarity(q_norm, emb)
            results.append((key, sim))

        results.sort(key=lambda x: x[1], reverse=True)

        output: list[dict[str, Any]] = []
        for key, score in results[:top_k]:
            entry = self._vector[key]
            output.append(
                {
                    "key": key,
                    "text": entry["text"],
                    "score": round(score, 4),
                    "metadata": entry["metadata"],
                }
            )
        return output

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self) -> dict[str, int]:
        """Remove expired entries. Returns counts of removed items."""
        now = time.time()
        removed = {"session": 0, "vector": 0}

        for sid in list(self._session.keys()):
            expired = [k for k, v in self._session[sid].items() if v["expires_at"] < now]
            for k in expired:
                del self._session[sid][k]
                removed["session"] += 1
            if not self._session[sid]:
                del self._session[sid]

        for key in list(self._vector.keys()):
            if now - self._vector[key]["timestamp"] > 86400:
                del self._vector[key]
                removed["vector"] += 1

        return removed

    def get_stats(self) -> dict[str, int]:
        return {
            "conversation_sessions": len(self._conversation),
            "active_sessions": len(self._session),
            "task_memories": len(self._task),
            "shared_entries": len(self._shared),
            "vector_entries": len(self._vector),
        }


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# Singleton
_memory_store: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store
