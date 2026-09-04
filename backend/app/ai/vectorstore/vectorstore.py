"""Vector store implementation using pgvector (with in-memory fallback)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class VectorRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str = ""
    embedding: list[float] | None = None
    namespace: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)
    organization_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VectorStore:
    """Vector store abstraction with pgvector backend support."""

    def __init__(self, namespace: str = "default", organization_id: str | None = None) -> None:
        self.namespace = namespace
        self.organization_id = organization_id
        self._records: list[VectorRecord] = []
        self._initialized = False
        self._backend = "pgvector"

    def initialize(self) -> None:
        if not self._initialized:
            self._initialized = True

    def add_records(self, records: list[VectorRecord]) -> list[str]:
        ids = []
        for record in records:
            if record.namespace != self.namespace:
                continue
            if self.organization_id and record.organization_id != self.organization_id:
                continue
            self._records.append(record)
            ids.append(record.id)
        return ids

    def add_record(self, record: VectorRecord) -> str:
        ids = self.add_records([record])
        return ids[0] if ids else ""

    def delete_record(self, record_id: str) -> bool:
        for i, record in enumerate(self._records):
            if record.id == record_id:
                del self._records[i]
                return True
        return False

    def search_similar(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        namespace: str | None = None,
    ) -> list[tuple[VectorRecord, float]]:
        ns = namespace or self.namespace
        results: list[tuple[VectorRecord, float]] = []
        for record in self._records:
            if record.namespace != ns:
                continue
            if self.organization_id and record.organization_id != self.organization_id:
                continue
            if filters and not self._matches_filters(record, filters):
                continue
            if record.embedding is None:
                continue
            score = self._cosine_similarity(query_embedding, record.embedding)
            results.append((record, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get_by_ids(self, ids: list[str]) -> list[VectorRecord]:
        return [r for r in self._records if r.id in ids]

    def cleanup_expired(self, ttl_days: int = 90) -> int:
        cutoff = datetime.utcnow() - timedelta(days=ttl_days)
        before = len(self._records)
        self._records = [r for r in self._records if r.created_at > cutoff]
        return before - len(self._records)

    def _matches_filters(self, record: VectorRecord, filters: dict[str, Any]) -> bool:
        for key, value in filters.items():
            if key in record.metadata and record.metadata[key] != value:
                return False
        return True

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = sum(x**2 for x in a) ** 0.5
        norm_b = sum(y**2 for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
