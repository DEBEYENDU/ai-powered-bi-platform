from __future__ import annotations

import json
import time

from sqlalchemy.orm import Session

from app.knowledge.models.chunk import DocumentChunk
from app.knowledge.repositories.chunk_repository import ChunkRepository
from app.knowledge.repositories.collection_repository import CollectionRepository
from app.knowledge.repositories.document_repository import DocumentRepository
from app.knowledge.services.chunking_service import ChunkingService
from app.knowledge.services.embedding_service import EmbeddingService


class IndexingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = ChunkRepository(db)
        self.collection_repo = CollectionRepository(db)
        self.chunking_service = ChunkingService()
        self.embedding_service = EmbeddingService()

    async def index_document(self, document_id: str, organization_id: str) -> dict:
        start = time.time()
        document = self.doc_repo.get(document_id, organization_id)
        if not document:
            return {"error": f"Document {document_id} not found"}

        self.doc_repo.update(document, status="processing", error_message=None)

        try:
            content_text = document.content_text or ""
            if not content_text:
                self.doc_repo.update(
                    document, status="failed", error_message="No content text found"
                )
                return {"error": "No content text found", "document_id": document_id}

            metadata = {
                "document_id": document_id,
                "filename": document.filename,
                "collection_id": document.collection_id,
            }
            chunks = self.chunking_service.chunk_text(content_text, metadata)

            if not chunks:
                self.doc_repo.update(document, status="indexed", chunk_count=0)
                return {
                    "document_id": document_id,
                    "chunks_created": 0,
                    "embeddings_generated": 0,
                    "duration_ms": round((time.time() - start) * 1000, 2),
                }

            texts = [c["text"] for c in chunks]
            embeddings = await self.embedding_service.embed_batch(texts)

            db_chunks: list[DocumentChunk] = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                meta = chunk["metadata"]
                db_chunk = DocumentChunk(
                    document_id=document_id,
                    organization_id=organization_id,
                    collection_id=document.collection_id,
                    chunk_index=chunk["chunk_index"],
                    text=chunk["text"],
                    token_count=meta.get("word_count", 0),
                    character_count=meta.get("char_count", len(chunk["text"])),
                    page_number=meta.get("page_number"),
                    section=meta.get("section"),
                    metadata_json=json.dumps(meta),
                    embedding=embedding,
                    embedding_model="deterministic"
                    if not self._has_openai_key()
                    else "text-embedding-ada-002",
                    embedding_dimensions=self.embedding_service.get_dimensions(),
                    embedding_status="generated",
                )
                db_chunks.append(db_chunk)

            self.chunk_repo.create_many(db_chunks)

            self.doc_repo.update(document, status="indexed", chunk_count=len(db_chunks))

            if document.collection_id:
                self.collection_repo.update_counts(
                    document.collection_id, doc_delta=0, chunk_delta=len(db_chunks)
                )

            duration_ms = round((time.time() - start) * 1000, 2)

            return {
                "document_id": document_id,
                "chunks_created": len(db_chunks),
                "embeddings_generated": len(db_chunks),
                "duration_ms": duration_ms,
            }

        except Exception as exc:
            self.doc_repo.update(document, status="failed", error_message=str(exc))
            return {
                "error": str(exc),
                "document_id": document_id,
                "duration_ms": round((time.time() - start) * 1000, 2),
            }

    async def reindex_document(self, document_id: str, organization_id: str) -> dict:
        existing_count = self.chunk_repo.delete_by_document(document_id, organization_id)
        document = self.doc_repo.get(document_id, organization_id)
        if document:
            self.doc_repo.update(document, status="processing", error_message=None)

        return await self.index_document(document_id, organization_id)

    def _has_openai_key(self) -> bool:
        from app.core.config import get_settings

        return bool(get_settings().openai_api_key)
