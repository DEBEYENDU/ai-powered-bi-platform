"""Celery tasks for background document indexing and re-indexing."""

from __future__ import annotations

import logging

from app.db.session import get_db_session

log = logging.getLogger(__name__)

try:
    from app.workers.celery_app import celery_app
except ImportError:
    celery_app = None  # type: ignore[assignment]


def _get_celery_app():
    if celery_app is None:
        raise RuntimeError("Celery is not configured. Install celery and set REDIS_URL.")
    return celery_app


def _index_document_sync(document_id: str, organization_id: str) -> dict:
    """Synchronous document indexing logic used by both Celery tasks and fallback."""
    from app.knowledge.repositories.chunk_repository import ChunkRepository
    from app.knowledge.repositories.collection_repository import CollectionRepository
    from app.knowledge.repositories.document_repository import DocumentRepository

    with get_db_session() as db:
        doc_repo = DocumentRepository(db)
        chunk_repo = ChunkRepository(db)
        col_repo = CollectionRepository(db)

        doc = doc_repo.get(document_id, organization_id)
        if doc is None:
            log.error(
                "document_not_found_for_indexing doc_id=%s org_id=%s", document_id, organization_id
            )
            return {"status": "error", "error": "Document not found"}

        doc_repo.update(doc, status="processing", error_message=None)

        try:
            from app.knowledge.extractors.factory import ExtractorFactory

            factory = ExtractorFactory()
            extractor = factory.get_extractor(doc.content_type)
            content_text = extractor.extract(doc.storage_path)
        except ImportError:
            log.warning(
                "ExtractorFactory not available, falling back to raw file read for doc %s",
                document_id,
            )
            try:
                from pathlib import Path

                file_path = Path(doc.storage_path)
                if file_path.exists():
                    content_text = file_path.read_text(encoding="utf-8", errors="replace")
                else:
                    content_text = ""
            except Exception as read_err:
                doc_repo.update(
                    doc, status="failed", error_message=f"Text extraction failed: {read_err}"
                )
                return {"status": "failed", "error": str(read_err)}
        except Exception as ext_err:
            doc_repo.update(
                doc, status="failed", error_message=f"Text extraction failed: {ext_err}"
            )
            return {"status": "failed", "error": str(ext_err)}

        doc_repo.update(doc, content_text=content_text)

        chunk_repo.delete_by_document(document_id, organization_id)

        try:
            chunk_size = 500
            chunk_overlap = 50
            chunks_text: list[str] = []
            start = 0
            while start < len(content_text):
                end = min(start + chunk_size, len(content_text))
                chunks_text.append(content_text[start:end])
                start += chunk_size - chunk_overlap

            from app.knowledge.models.chunk import DocumentChunk

            chunk_models = []
            for idx, text_piece in enumerate(chunks_text):
                chunk_models.append(
                    DocumentChunk(
                        document_id=document_id,
                        organization_id=organization_id,
                        collection_id=doc.collection_id,
                        chunk_index=idx,
                        text=text_piece,
                        token_count=len(text_piece.split()),
                        character_count=len(text_piece),
                        embedding_status="pending",
                    )
                )

            created_chunks = chunk_repo.create_many(chunk_models) if chunk_models else []

            try:
                from app.ai.embeddings.manager import EmbeddingManager

                embedder = EmbeddingManager()
                embedder.initialize()
                for chunk in created_chunks:
                    embedding = embedder.get_embedding(chunk.text)
                    chunk.embedding = embedding
                    chunk.embedding_model = embedder.config.model
                    chunk.embedding_dimensions = embedder.config.dimensions
                    chunk.embedding_status = "generated"
                db.commit()
            except ImportError:
                log.warning(
                    "EmbeddingManager not available, chunks stored without embeddings for doc %s",
                    document_id,
                )
            except Exception as emb_err:
                log.warning("Embedding generation failed for doc %s: %s", document_id, emb_err)

            doc_repo.update(
                doc,
                status="indexed",
                chunk_count=len(created_chunks),
                indexed_at=__import__("datetime").datetime.utcnow(),
            )

            if doc.collection_id:
                try:
                    col_repo.update_counts(doc.collection_id, 0, len(created_chunks))
                except Exception:
                    pass

            return {"status": "indexed", "chunks_created": len(created_chunks)}

        except Exception as chunk_err:
            doc_repo.update(
                doc, status="failed", error_message=f"Chunking/indexing failed: {chunk_err}"
            )
            return {"status": "failed", "error": str(chunk_err)}


def _reindex_document_sync(document_id: str, organization_id: str) -> dict:
    """Synchronous re-indexing: clears chunks and re-runs indexing."""
    from app.knowledge.repositories.chunk_repository import ChunkRepository
    from app.knowledge.repositories.collection_repository import CollectionRepository
    from app.knowledge.repositories.document_repository import DocumentRepository

    with get_db_session() as db:
        doc_repo = DocumentRepository(db)
        chunk_repo = ChunkRepository(db)
        col_repo = CollectionRepository(db)

        doc = doc_repo.get(document_id, organization_id)
        if doc is None:
            return {"status": "error", "error": "Document not found"}

        old_chunk_count = doc.chunk_count

        doc_repo.reindex(doc)

        deleted = chunk_repo.delete_by_document(document_id, organization_id)

        if doc.collection_id and deleted > 0:
            try:
                col_repo.update_counts(doc.collection_id, 0, -deleted)
            except Exception:
                pass

    return _index_document_sync(document_id, organization_id)


if celery_app is not None:
    _app = _get_celery_app()

    @_app.task(bind=True, max_retries=3, default_retry_delay=30)
    def index_document_task(self, document_id: str, organization_id: str):
        """Background task to index a document.

        Chunks the document text, generates embeddings, and stores chunks.
        Retries up to 3 times on transient failures.
        """
        try:
            result = _index_document_sync(document_id, organization_id)
            if result.get("status") == "failed":
                raise RuntimeError(result.get("error", "Indexing failed"))
            return result
        except Exception as exc:
            log.error(
                "index_document_task_failed doc_id=%s org_id=%s attempt=%s error=%s",
                document_id,
                organization_id,
                self.request.retries,
                exc,
            )
            try:
                self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                from app.knowledge.repositories.document_repository import DocumentRepository

                with get_db_session() as db:
                    doc_repo = DocumentRepository(db)
                    doc = doc_repo.get(document_id, organization_id)
                    if doc is not None:
                        doc_repo.update(
                            doc,
                            status="failed",
                            error_message=f"Indexing failed after {self.max_retries} retries: {exc}",
                        )
                return {"status": "failed", "error": str(exc)}

    @_app.task(bind=True, max_retries=3, default_retry_delay=30)
    def reindex_document_task(self, document_id: str, organization_id: str):
        """Background task to re-index a document.

        Deletes existing chunks, re-extracts text, re-chunks, and re-embeds.
        """
        try:
            result = _reindex_document_sync(document_id, organization_id)
            if result.get("status") == "failed":
                raise RuntimeError(result.get("error", "Re-indexing failed"))
            return result
        except Exception as exc:
            log.error(
                "reindex_document_task_failed doc_id=%s org_id=%s attempt=%s error=%s",
                document_id,
                organization_id,
                self.request.retries,
                exc,
            )
            try:
                self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                from app.knowledge.repositories.document_repository import DocumentRepository

                with get_db_session() as db:
                    doc_repo = DocumentRepository(db)
                    doc = doc_repo.get(document_id, organization_id)
                    if doc is not None:
                        doc_repo.update(
                            doc,
                            status="failed",
                            error_message=f"Re-indexing failed after {self.max_retries} retries: {exc}",
                        )
                return {"status": "failed", "error": str(exc)}


else:
    # Fallback: allow direct import for synchronous execution when Celery is unavailable.
    def index_document_task(document_id: str, organization_id: str) -> dict:  # type: ignore[misc]
        return _index_document_sync(document_id, organization_id)

    def reindex_document_task(document_id: str, organization_id: str) -> dict:  # type: ignore[misc]
        return _reindex_document_sync(document_id, organization_id)
