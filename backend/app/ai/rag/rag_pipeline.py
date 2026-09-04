"""RAG pipeline for AI Business Assistant."""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel

from app.ai.cache.caching import AICache
from app.ai.embeddings.manager import EmbeddingManager
from app.ai.retrieval.retriever import RetrievalResult, Retriever


class RAGConfig(BaseModel):
    top_k: int = 10
    semantic_weight: float = 0.7
    keyword_weight: float = 0.3
    min_relevance_score: float = 0.3
    chunk_size: int = 500
    chunk_overlap: int = 50


class RAGResult(BaseModel):
    query: str
    retrieved_contexts: list[RetrievalResult]
    assembled_context: str
    confidence_score: float
    citation_count: int
    retrieval_time_ms: float


class RAGPipeline:
    """End-to-end RAG pipeline."""

    def __init__(self, config: RAGConfig | None = None) -> None:
        self.config = config or RAGConfig()
        self.embedder = EmbeddingManager()
        self.retriever = Retriever(
            semantic_weight=self.config.semantic_weight,
            keyword_weight=self.config.keyword_weight,
        )
        self.cache = AICache()
        self._initialized = False

    def initialize(self) -> None:
        if not self._initialized:
            self.embedder.initialize()
            self._initialized = True

    def index_document(
        self,
        content: str,
        source: str,
        source_type: str = "document",
        metadata: dict[str, Any] | None = None,
        chunk: bool = True,
    ) -> int:
        self.initialize()
        chunks = self._chunk_text(content) if chunk else [content]
        count = 0
        for chunk_text in chunks:
            embedding = self.embedder.get_embedding(chunk_text)
            self.retriever.add_document(
                content=chunk_text,
                source=source,
                source_type=source_type,
                metadata=metadata or {},
                embeddings=embedding,
            )
            count += 1
        return count

    def index_documents_batch(self, documents: list[dict[str, Any]]) -> int:
        count = 0
        for doc in documents:
            count += self.index_document(
                content=doc.get("content", ""),
                source=doc.get("source", ""),
                source_type=doc.get("source_type", "document"),
                metadata=doc.get("metadata"),
            )
        return count

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> RAGResult:
        self.initialize()
        start = time.time()
        cache_key = f"rag:{hash(query) % 1000000000}:{top_k or self.config.top_k}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        query_embedding = self.embedder.get_embedding(query)
        top_k = top_k or self.config.top_k
        retrieval_results = self.retriever.retrieve_for_query(query, query_embedding, top_k=top_k)
        filtered = []
        for result in retrieval_results:
            if result.score < self.config.min_relevance_score:
                continue
            if filters and not all(result.metadata.get(k) == v for k, v in filters.items()):
                continue
            filtered.append(result)
        assembled = self._assemble_context(filtered)
        confidence = self._calculate_confidence(filtered)
        rag_result = RAGResult(
            query=query,
            retrieved_contexts=filtered,
            assembled_context=assembled,
            confidence_score=confidence,
            citation_count=len(filtered),
            retrieval_time_ms=round((time.time() - start) * 1000, 2),
        )
        self.cache.set(cache_key, rag_result, ttl=300.0)
        return rag_result

    def _assemble_context(self, results: list[RetrievalResult]) -> str:
        parts = []
        for result in results:
            parts.append(f"[Source: {result.source}] {result.content}")
        return "\n---\n".join(parts)

    def _calculate_confidence(self, results: list[RetrievalResult]) -> float:
        if not results:
            return 0.0
        avg_score = sum(r.score for r in results) / len(results)
        return min(1.0, avg_score * 1.2)

    def _chunk_text(self, text: str) -> list[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.config.chunk_size, len(text))
            chunks.append(text[start:end])
            start += self.config.chunk_size - self.config.chunk_overlap
        return chunks

    def get_stats(self) -> dict[str, Any]:
        return {
            "documents_indexed": self.retriever.get_knowledge_base_size(),
            "embedding_model": self.embedder.config.model,
        }
