from __future__ import annotations

import hashlib
import math
import struct

from app.core.config import get_settings


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._dimensions = 1536

    async def embed_text(self, text: str) -> list[float]:
        if self.settings.openai_api_key:
            return await self._openai_embed(text)
        return self._deterministic_embedding(text)

    async def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        if not texts:
            return []

        if self.settings.openai_api_key:
            all_embeddings: list[list[float]] = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                batch_embeddings = await self._openai_embed_batch(batch)
                all_embeddings.extend(batch_embeddings)
            return all_embeddings

        return [self._deterministic_embedding(t) for t in texts]

    async def _openai_embed(self, text: str) -> list[float]:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.settings.openai_base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "text-embedding-ada-002",
                    "input": text,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            embedding = data["data"][0]["embedding"]
            self._dimensions = len(embedding)
            return embedding

    async def _openai_embed_batch(self, texts: list[str]) -> list[list[float]]:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.settings.openai_base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "text-embedding-ada-002",
                    "input": texts,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            embeddings = [item["embedding"] for item in data["data"]]
            if embeddings:
                self._dimensions = len(embeddings[0])
            return embeddings

    def _deterministic_embedding(self, text: str, dimensions: int = 1536) -> list[float]:
        digest = hashlib.sha512(text.encode("utf-8")).digest()

        seed_bytes = digest[:8]
        seed = struct.unpack("<Q", seed_bytes)[0]

        values: list[float] = []
        byte_index = 8

        while len(values) < dimensions:
            if byte_index + 4 > len(digest):
                digest = hashlib.sha512(digest).digest()
                byte_index = 0

            raw = struct.unpack("<I", digest[byte_index : byte_index + 4])[0]
            byte_index += 4

            normalized = (raw / 0xFFFFFFFF) * 2.0 - 1.0
            values.append(normalized)

        norm = math.sqrt(sum(v * v for v in values))
        if norm > 0:
            values = [v / norm for v in values]

        return values

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            raise ValueError("Vectors must have same length")

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def get_dimensions(self) -> int:
        return self._dimensions
