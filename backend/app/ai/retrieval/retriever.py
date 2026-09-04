"""Retrieval engine for AI Business Assistant."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RetrievalResult(BaseModel):
    content: str
    source: str
    source_type: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


class HybridSearchResult(BaseModel):
    semantic_results: list[RetrievalResult] = Field(default_factory=list)
    keyword_results: list[RetrievalResult] = Field(default_factory=list)
    combined_results: list[RetrievalResult] = Field(default_factory=list)


class Retriever:
    """Hybrid retrieval combining semantic and keyword search."""

    def __init__(self, semantic_weight: float = 0.7, keyword_weight: float = 0.3) -> None:
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        self._knowledge_base: list[dict[str, Any]] = []

    def add_document(
        self,
        content: str,
        source: str,
        source_type: str = "document",
        metadata: dict[str, Any] | None = None,
        embeddings: list[float] | None = None,
    ) -> None:
        self._knowledge_base.append(
            {
                "content": content,
                "source": source,
                "source_type": source_type,
                "metadata": metadata or {},
                "keywords": self._extract_keywords(content),
                "embeddings": embeddings,
            }
        )

    def add_documents_batch(self, docs: list[dict[str, Any]]) -> None:
        for doc in docs:
            self.add_document(**doc)

    def semantic_search(
        self, query_embedding: list[float], top_k: int = 10
    ) -> list[RetrievalResult]:
        results = []
        for doc in self._knowledge_base:
            if doc["embeddings"] is None:
                continue
            score = self._cosine_similarity(query_embedding, doc["embeddings"])
            results.append(
                RetrievalResult(
                    content=doc["content"],
                    source=doc["source"],
                    source_type=doc["source_type"],
                    score=score,
                    metadata=doc["metadata"],
                )
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def keyword_search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        query_keywords = set(query.lower().split())
        results = []
        for doc in self._knowledge_base:
            doc_keywords = set(kw.lower() for kw in doc.get("keywords", []))
            if not doc_keywords:
                continue
            overlap = len(query_keywords & doc_keywords)
            if overlap > 0:
                score = overlap / max(len(doc_keywords), 1)
                results.append(
                    RetrievalResult(
                        content=doc["content"],
                        source=doc["source"],
                        source_type=doc["source_type"],
                        score=score,
                        metadata=doc["metadata"],
                    )
                )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def hybrid_search(
        self, query: str, query_embedding: list[float] | None = None, top_k: int = 10
    ) -> HybridSearchResult:
        semantic = []
        keyword = []
        if query_embedding is not None:
            semantic = self.semantic_search(query_embedding, top_k=top_k * 2)
        keyword = self.keyword_search(query, top_k=top_k * 2)

        combined_map: dict[str, RetrievalResult] = {}
        for r in semantic:
            combined_map.setdefault(r.source + r.content[:50], r)
            r.score = self.semantic_weight * r.score + self.keyword_weight * 0.5
        for r in keyword:
            key = r.source + r.content[:50]
            if key in combined_map:
                combined_map[key].score = (
                    combined_map[key].score * 0.5 + self.keyword_weight * r.score
                )
            else:
                r.score = self.keyword_weight * r.score
                combined_map[key] = r

        combined = sorted(combined_map.values(), key=lambda r: r.score, reverse=True)
        return HybridSearchResult(
            semantic_results=semantic,
            keyword_results=keyword,
            combined_results=combined[:top_k],
        )

    def retrieve_for_query(
        self, query: str, query_embedding: list[float] | None = None, top_k: int = 10
    ) -> list[RetrievalResult]:
        hybrid = self.hybrid_search(query, query_embedding, top_k)
        return hybrid.combined_results

    def get_knowledge_base_size(self) -> int:
        return len(self._knowledge_base)

    def _extract_keywords(self, text: str) -> list[str]:
        import re

        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        from collections import Counter

        return [w for w, _ in Counter(words).most_common(20)]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = sum(x**2 for x in a) ** 0.5
        norm_b = sum(y**2 for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
