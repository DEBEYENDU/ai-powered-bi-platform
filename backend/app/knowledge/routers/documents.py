"""Document management endpoints for the Knowledge Base."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.admin.services.platform import PlatformAdmin
from app.core.config import get_settings
from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization
from app.exceptions.handlers import AppError, NotFoundError
from app.knowledge.repositories.chunk_repository import ChunkRepository
from app.knowledge.repositories.collection_repository import CollectionRepository
from app.knowledge.repositories.document_repository import DocumentRepository

documents_router = APIRouter(prefix="/documents", tags=["Knowledge Documents"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
SUPPORTED_TYPES = {".txt", ".md", ".markdown", ".pdf", ".docx", ".doc", ".csv"}


def _doc_response(doc) -> dict:
    return {
        "id": doc.id,
        "organization_id": doc.organization_id,
        "collection_id": doc.collection_id,
        "filename": doc.filename,
        "original_filename": doc.original_filename,
        "content_type": doc.content_type,
        "file_size": doc.file_size,
        "title": doc.title,
        "description": doc.description,
        "source_type": doc.source_type,
        "status": doc.status,
        "error_message": doc.error_message,
        "created_by": doc.created_by,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        "indexed_at": doc.indexed_at.isoformat() if doc.indexed_at else None,
        "version": doc.version,
        "chunk_count": doc.chunk_count,
        "checksum": doc.checksum,
    }


@documents_router.post("", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
    collection_id: str | None = Form(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Upload a document to the knowledge base.

    - Validates file type and size
    - Stores file securely using storage_path
    - Computes SHA-256 checksum for deduplication
    - Extracts text content
    - Queues background indexing job
    """
    settings = get_settings()
    user_id: str = user.get("sub") or user.get("user_id") or ""

    # 1. Validate file type
    if not file.filename:
        raise AppError("Filename is required")
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_TYPES:
        raise AppError(
            f"Unsupported file type '{ext}'. Supported types: {', '.join(sorted(SUPPORTED_TYPES))}"
        )

    # 2. Read file content and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise AppError(
            f"File size ({len(content)} bytes) exceeds maximum allowed size "
            f"({MAX_FILE_SIZE} bytes / 50MB)"
        )

    # 3. Compute SHA-256 checksum for deduplication
    checksum = hashlib.sha256(content).hexdigest()

    # 4. Check for duplicate (same org + checksum)
    doc_repo = DocumentRepository(db)
    existing = doc_repo.get_by_checksum(organization_id, checksum)
    if existing is not None:
        raise AppError(
            f"A document with identical content already exists "
            f"(document id: {existing.id}, filename: {existing.original_filename})"
        )

    # 5. Validate collection if provided
    if collection_id:
        col_repo = CollectionRepository(db)
        collection = col_repo.get(collection_id, organization_id)
        if collection is None:
            raise NotFoundError("Collection not found")

    # 6. Generate document ID and storage path
    from app.knowledge.models.document import KnowledgeDocument

    doc_id = uuid.uuid4().hex[:12]
    safe_filename = f"{doc_id}_{file.filename}"
    storage_dir = settings.storage_dir / "knowledge" / organization_id / doc_id
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = str(storage_dir / safe_filename)

    # 7. Save file to storage
    with open(storage_path, "wb") as f:
        f.write(content)

    # 8. Create document record with status=pending
    doc = KnowledgeDocument(
        id=doc_id,
        organization_id=organization_id,
        collection_id=collection_id,
        filename=safe_filename,
        original_filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        storage_path=storage_path,
        checksum=checksum,
        title=title or Path(file.filename).stem,
        description=description,
        source_type="upload",
        status="pending",
        created_by=user_id or None,
    )
    doc = doc_repo.create(doc)

    # 9. Extract text using ExtractorFactory (best-effort)
    try:
        from app.knowledge.extractors.factory import ExtractorFactory

        factory = ExtractorFactory()
        extractor = factory.get_extractor(doc.content_type)
        content_text = extractor.extract(storage_path)
        doc_repo.update(doc, content_text=content_text)
    except ImportError:
        try:
            if ext in {".txt", ".md", ".markdown", ".csv"}:
                content_text = content.decode("utf-8", errors="replace")
                doc_repo.update(doc, content_text=content_text)
        except Exception:
            pass
    except Exception:
        pass

    # 10. Queue indexing via Celery (with fallback to sync)
    try:
        from app.knowledge.tasks import index_document_task

        task = index_document_task.delay(doc_id, organization_id)
        doc_repo.update(doc, status="processing")
    except Exception:
        try:
            from app.knowledge.tasks import _index_document_sync

            result = _index_document_sync(doc_id, organization_id)
        except Exception:
            doc_repo.update(doc, status="pending")

    # 11. Audit log
    try:
        platform = PlatformAdmin()
        platform.audit.append(
            "document_uploaded",
            "document",
            doc_id,
            actor_id=user_id or None,
            organization_id=organization_id,
            details={
                "filename": file.filename,
                "file_size": len(content),
                "checksum": checksum,
                "collection_id": collection_id,
            },
        )
    except Exception:
        pass

    # 12. Record metrics
    try:
        platform.metrics.record(
            "knowledge_document_uploaded",
            1.0,
            labels={"organization_id": organization_id, "file_type": ext},
        )
    except Exception:
        pass

    return _doc_response(doc)


@documents_router.get("")
async def list_documents(
    collection_id: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """List documents with filtering and pagination."""
    doc_repo = DocumentRepository(db)
    offset = (page - 1) * page_size
    docs, total = doc_repo.list(
        organization_id=organization_id,
        collection_id=collection_id,
        status=status,
        limit=page_size,
        offset=offset,
    )
    return {
        "data": [_doc_response(d) for d in docs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@documents_router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Get document details."""
    doc_repo = DocumentRepository(db)
    doc = doc_repo.get(document_id, organization_id)
    if doc is None:
        raise NotFoundError("Document not found")
    return _doc_response(doc)


@documents_router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Delete a document and its chunks. Removes file from storage."""
    user_id: str = user.get("sub") or user.get("user_id") or ""

    doc_repo = DocumentRepository(db)
    chunk_repo = ChunkRepository(db)
    col_repo = CollectionRepository(db)

    doc = doc_repo.get(document_id, organization_id)
    if doc is None:
        raise NotFoundError("Document not found")

    # Delete chunks
    deleted_chunks = chunk_repo.delete_by_document(document_id, organization_id)

    # Soft-delete document
    doc_repo.soft_delete(doc)

    # Update collection counts
    if doc.collection_id and deleted_chunks > 0:
        try:
            col_repo.update_counts(doc.collection_id, -1, -deleted_chunks)
        except Exception:
            pass

    # Remove file from storage (best-effort)
    try:
        file_path = Path(doc.storage_path)
        if file_path.exists():
            file_path.unlink()
        parent_dir = file_path.parent
        if parent_dir.exists() and not any(parent_dir.iterdir()):
            parent_dir.rmdir()
    except Exception:
        pass

    # Audit log
    try:
        platform = PlatformAdmin()
        platform.audit.append(
            "document_deleted",
            "document",
            document_id,
            actor_id=user_id or None,
            organization_id=organization_id,
            details={
                "filename": doc.original_filename,
                "chunks_deleted": deleted_chunks,
                "collection_id": doc.collection_id,
            },
        )
    except Exception:
        pass

    # Record metrics
    try:
        platform.metrics.record(
            "knowledge_document_deleted",
            1.0,
            labels={"organization_id": organization_id},
        )
    except Exception:
        pass

    return None


@documents_router.post("/{document_id}/reindex")
async def reindex_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Re-index a document: re-chunk and re-embed."""
    user_id: str = user.get("sub") or user.get("user_id") or ""

    doc_repo = DocumentRepository(db)
    doc = doc_repo.get(document_id, organization_id)
    if doc is None:
        raise NotFoundError("Document not found")

    # Reset status to processing
    doc_repo.reindex(doc)

    # Queue re-indexing via Celery (with fallback to sync)
    try:
        from app.knowledge.tasks import reindex_document_task

        task = reindex_document_task.delay(document_id, organization_id)
    except Exception:
        try:
            from app.knowledge.tasks import _reindex_document_sync

            _reindex_document_sync(document_id, organization_id)
        except Exception:
            pass

    # Audit log
    try:
        platform = PlatformAdmin()
        platform.audit.append(
            "document_reindexed",
            "document",
            document_id,
            actor_id=user_id or None,
            organization_id=organization_id,
            details={"filename": doc.original_filename},
        )
    except Exception:
        pass

    return {"status": "processing", "document_id": document_id}


@documents_router.get("/{document_id}/status")
async def get_document_status(
    document_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Get document indexing status."""
    doc_repo = DocumentRepository(db)
    doc = doc_repo.get(document_id, organization_id)
    if doc is None:
        raise NotFoundError("Document not found")

    chunk_repo = ChunkRepository(db)
    chunks = chunk_repo.get_by_document(document_id, organization_id)

    embedding_status_counts: dict[str, int] = {}
    for chunk in chunks:
        s = chunk.embedding_status or "unknown"
        embedding_status_counts[s] = embedding_status_counts.get(s, 0) + 1

    return {
        "document_id": document_id,
        "status": doc.status,
        "error_message": doc.error_message,
        "chunk_count": doc.chunk_count,
        "embedding_status": embedding_status_counts,
        "indexed_at": doc.indexed_at.isoformat() if doc.indexed_at else None,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


@documents_router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Get chunks for a document."""
    doc_repo = DocumentRepository(db)
    doc = doc_repo.get(document_id, organization_id)
    if doc is None:
        raise NotFoundError("Document not found")

    chunk_repo = ChunkRepository(db)
    chunks = chunk_repo.get_by_document(document_id, organization_id)

    return {
        "document_id": document_id,
        "chunks": [
            {
                "id": c.id,
                "chunk_index": c.chunk_index,
                "text": c.text,
                "token_count": c.token_count,
                "character_count": c.character_count,
                "page_number": c.page_number,
                "section": c.section,
                "embedding_status": c.embedding_status,
                "embedding_model": c.embedding_model,
                "embedding_dimensions": c.embedding_dimensions,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in chunks
        ],
        "total": len(chunks),
    }
