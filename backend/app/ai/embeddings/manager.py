"""Embedding management for AI Business Assistant."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class EmbeddingConfig(BaseModel):
    model: str = Field(default="text-embedding-3-large", description="Embedding model")
    dimensions: int = Field(default=1536, description="Embedding dimensions")
    batch_size: int = Field(default=100, description="Batch size for embedding generation")
    normalize: bool = Field(default=True, description="Normalize embeddings")


class EmbeddingResult(BaseModel):
    text: str
    embedding: List[float]
    model: str
    token_count: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EmbeddingManager:
    """Manages text embeddings with caching."""

    def __init__(self, config: Optional[EmbeddingConfig] = None) -> None:
        self.config = config or EmbeddingConfig()
        self._cache: Dict[str, List[float]] = {}
        self._initialized = False

    def initialize(self) -> None:
        if not self._initialized:
            self._initialized = True

    def get_embedding(self, text: str) -> List[float]:
        cache_key = f"{self.config.model}:{hash(text) % 1000000000}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        embedding = self._generate_embedding(text)
        self._cache[cache_key] = embedding
        return embedding

    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self.get_embedding(text) for text in texts]

    def _generate_embedding(self, text: str) -> List[float]:
        import random
        dim = self.config.dimensions
        random.seed(hash(text) % (2**31))
        embedding = [random.gauss(0, 1) for _ in range(dim)]
        norm = sum(x ** 2 for x in embedding) ** 0.5
        if norm > 0 and self.config.normalize:
            embedding = [x / norm for x in embedding]
        return embedding

    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        if len(embedding1) != len(embedding2):
            return 0.0
        dot = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = sum(a ** 2 for a in embedding1) ** 0.5
        norm2 = sum(b ** 2 for b in embedding2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "model": self.config.model,
            "cache_size": len(self._cache),
            "dimensions": self.config.dimensions,
        }
