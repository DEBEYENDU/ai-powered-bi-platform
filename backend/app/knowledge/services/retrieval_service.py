from __future__ import annotations

from sqlalchemy.orm import Session

from app.knowledge.repositories.chunk_repository import ChunkRepository
from app.knowledge.services.embedding_service import EmbeddingService


class RetrievalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedding_service = EmbeddingService()
        self.chunk_repo = ChunkRepository(db)

    async def semantic_search(
        self,
        query: str,
        org_id: str,
        collection_ids: list[str] | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        query_embedding = await self.embedding_service.embed_text(query)

        results = self.chunk_repo.search_by_embedding(
            org_id=org_id,
            embedding=query_embedding,
            collection_ids=collection_ids,
            top_k=top_k,
        )

        return [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "text": chunk.text,
                "score": score,
                "page_number": chunk.page_number,
                "section": chunk.section,
                "chunk_index": chunk.chunk_index,
                "metadata_json": chunk.metadata_json,
                "search_type": "semantic",
            }
            for chunk, score in results
        ]

    def keyword_search(
        self,
        query: str,
        org_id: str,
        collection_ids: list[str] | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        chunks = self.chunk_repo.search_keyword(
            org_id=org_id,
            query=query,
            collection_ids=collection_ids,
            top_k=top_k,
        )

        results: list[dict] = []
        for rank, chunk in enumerate(chunks):
            score = 1.0 - (rank / max(len(chunks), 1))
            results.append(
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "text": chunk.text,
                    "score": score,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "chunk_index": chunk.chunk_index,
                    "metadata_json": chunk.metadata_json,
                    "search_type": "keyword",
                }
            )

        return results

    async def hybrid_search(
        self,
        query: str,
        org_id: str,
        collection_ids: list[str] | None = None,
        top_k: int = 10,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> list[dict]:
        semantic_results = await self.semantic_search(query, org_id, collection_ids, top_k=top_k)
        keyword_results = self.keyword_search(query, org_id, collection_ids, top_k=top_k)

        normalized_semantic = self._normalize_scores(semantic_results, "score")
        normalized_keyword = self._normalize_scores(keyword_results, "score")

        chunk_scores: dict[str, dict] = {}

        for result in normalized_semantic:
            cid = result["chunk_id"]
            chunk_scores[cid] = {
                **result,
                "semantic_score": result["score"],
                "keyword_score": 0.0,
                "combined_score": result["score"] * semantic_weight,
            }

        for result in normalized_keyword:
            cid = result["chunk_id"]
            if cid in chunk_scores:
                chunk_scores[cid]["keyword_score"] = result["score"]
                chunk_scores[cid]["combined_score"] += result["score"] * keyword_weight
            else:
                chunk_scores[cid] = {
                    **result,
                    "semantic_score": 0.0,
                    "keyword_score": result["score"],
                    "combined_score": result["score"] * keyword_weight,
                }

        ranked = sorted(chunk_scores.values(), key=lambda x: x["combined_score"], reverse=True)[
            :top_k
        ]

        for r in ranked:
            r["score"] = r["combined_score"]
            r["search_type"] = "hybrid"

        return ranked

    @staticmethod
    def _normalize_scores(results: list[dict], score_key: str = "score") -> list[dict]:
        if not results:
            return []

        scores = [r[score_key] for r in results]
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score

        if score_range == 0:
            for r in results:
                r[score_key] = 1.0
        else:
            for r in results:
                r[score_key] = (r[score_key] - min_score) / score_range

        return results
