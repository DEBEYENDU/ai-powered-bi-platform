import math

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.knowledge.models.chunk import DocumentChunk


class ChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_many(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        self.db.add_all(chunks)
        self.db.commit()
        for chunk in chunks:
            self.db.refresh(chunk)
        return chunks

    def get_by_document(
        self, doc_id: str, organization_id: str, limit: int | None = None
    ) -> list[DocumentChunk]:
        stmt = (
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == doc_id,
                DocumentChunk.organization_id == organization_id,
            )
            .order_by(DocumentChunk.chunk_index)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def delete_by_document(self, doc_id: str, organization_id: str) -> int:
        stmt = delete(DocumentChunk).where(
            DocumentChunk.document_id == doc_id,
            DocumentChunk.organization_id == organization_id,
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount  # type: ignore[return-value]

    def search_by_embedding(
        self,
        org_id: str,
        embedding: list[float],
        collection_ids: list[str] | None,
        top_k: int,
    ) -> list[tuple[DocumentChunk, float]]:
        base_filter = [
            DocumentChunk.organization_id == org_id,
            DocumentChunk.embedding_status == "generated",
        ]
        if collection_ids:
            base_filter.append(DocumentChunk.collection_id.in_(collection_ids))

        stmt = select(DocumentChunk).where(*base_filter)
        result = self.db.execute(stmt)
        all_chunks = list(result.scalars().all())

        if not all_chunks:
            return []

        def cosine_similarity(a: list[float], b: list[float]) -> float:
            dot_product = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot_product / (norm_a * norm_b)

        scored: list[tuple[DocumentChunk, float]] = []
        for chunk in all_chunks:
            if chunk.embedding is None:
                continue
            score = cosine_similarity(embedding, chunk.embedding)
            scored.append((chunk, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def search_keyword(
        self,
        org_id: str,
        query: str,
        collection_ids: list[str] | None,
        top_k: int,
    ) -> list[DocumentChunk]:
        ts_query = func.plainto_tsquery("english", query)

        base_filter = [
            DocumentChunk.organization_id == org_id,
            DocumentChunk.keyword_tsv.op("@@")(ts_query),
        ]
        if collection_ids:
            base_filter.append(DocumentChunk.collection_id.in_(collection_ids))

        rank_expr = func.ts_rank(DocumentChunk.keyword_tsv, ts_query)

        stmt = select(DocumentChunk).where(*base_filter).order_by(rank_expr.desc()).limit(top_k)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def count_by_organization(self, org_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.organization_id == org_id)
        )
        result = self.db.execute(stmt)
        return result.scalar_one()

    def update_embedding_status(self, chunk_id: str, status: str) -> None:
        stmt = select(DocumentChunk).where(DocumentChunk.id == chunk_id)
        result = self.db.execute(stmt)
        chunk = result.scalar_one_or_none()
        if chunk is not None:
            chunk.embedding_status = status
            self.db.commit()
