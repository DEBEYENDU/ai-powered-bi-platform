"""Collection management endpoints for the Knowledge Base."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.admin.services.platform import PlatformAdmin
from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization
from app.exceptions.handlers import AppError, NotFoundError
from app.knowledge.repositories.chunk_repository import ChunkRepository
from app.knowledge.repositories.collection_repository import CollectionRepository
from app.knowledge.repositories.document_repository import DocumentRepository

collections_router = APIRouter(prefix="/collections", tags=["Knowledge Collections"])


def _col_response(col) -> dict:
    return {
        "id": col.id,
        "organization_id": col.organization_id,
        "name": col.name,
        "description": col.description,
        "access_policy": col.access_policy,
        "created_by": col.created_by,
        "created_at": col.created_at.isoformat() if col.created_at else None,
        "updated_at": col.updated_at.isoformat() if col.updated_at else None,
        "document_count": col.document_count,
        "total_chunks": col.total_chunks,
    }


@collections_router.post("", status_code=201)
async def create_collection(
    name: str = Body(...),
    description: str | None = Body(None),
    access_policy: str = Body("organization"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Create a new knowledge collection."""
    user_id: str = user.get("sub") or user.get("user_id") or ""
    col_repo = CollectionRepository(db)

    # Check for duplicate name within the organization
    existing = col_repo.get_by_name(organization_id, name)
    if existing is not None:
        raise AppError(f"A collection named '{name}' already exists in this organization")

    from app.knowledge.models.collection import KnowledgeCollection

    col = KnowledgeCollection(
        id=uuid.uuid4().hex[:12],
        organization_id=organization_id,
        name=name,
        description=description,
        access_policy=access_policy,
        created_by=user_id or None,
    )
    col = col_repo.create(col)

    # Audit log
    try:
        platform = PlatformAdmin()
        platform.audit.append(
            "collection_created",
            "collection",
            col.id,
            actor_id=user_id or None,
            organization_id=organization_id,
            details={"name": name, "access_policy": access_policy},
        )
    except Exception:
        pass

    # Record metrics
    try:
        platform.metrics.record(
            "knowledge_collection_created",
            1.0,
            labels={"organization_id": organization_id},
        )
    except Exception:
        pass

    return _col_response(col)


@collections_router.get("")
async def list_collections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """List collections with pagination."""
    col_repo = CollectionRepository(db)
    offset = (page - 1) * page_size
    cols, total = col_repo.list(
        organization_id=organization_id,
        limit=page_size,
        offset=offset,
    )
    return {
        "data": [_col_response(c) for c in cols],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@collections_router.get("/{collection_id}")
async def get_collection(
    collection_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Get collection details."""
    col_repo = CollectionRepository(db)
    col = col_repo.get(collection_id, organization_id)
    if col is None:
        raise NotFoundError("Collection not found")
    return _col_response(col)


@collections_router.patch("/{collection_id}")
async def update_collection(
    collection_id: str,
    name: str | None = Body(None),
    description: str | None = Body(None),
    access_policy: str | None = Body(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Update a collection's name, description, or access policy."""
    user_id: str = user.get("sub") or user.get("user_id") or ""
    col_repo = CollectionRepository(db)

    col = col_repo.get(collection_id, organization_id)
    if col is None:
        raise NotFoundError("Collection not found")

    update_fields: dict = {}
    if name is not None:
        # Check uniqueness if name is changing
        if name != col.name:
            existing = col_repo.get_by_name(organization_id, name)
            if existing is not None:
                raise AppError(f"A collection named '{name}' already exists in this organization")
        update_fields["name"] = name
    if description is not None:
        update_fields["description"] = description
    if access_policy is not None:
        update_fields["access_policy"] = access_policy

    if update_fields:
        col = col_repo.update(col, **update_fields)

    # Audit log
    try:
        platform = PlatformAdmin()
        platform.audit.append(
            "collection_updated",
            "collection",
            collection_id,
            actor_id=user_id or None,
            organization_id=organization_id,
            details=update_fields,
        )
    except Exception:
        pass

    return _col_response(col)


@collections_router.delete("/{collection_id}", status_code=204)
async def delete_collection(
    collection_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Delete a collection and optionally unlink its documents.

    Documents in the collection are unlinked (set to collection_id=None) but
    not deleted. Chunks belonging to the collection are removed.
    """
    user_id: str = user.get("sub") or user.get("user_id") or ""

    col_repo = CollectionRepository(db)
    doc_repo = DocumentRepository(db)
    chunk_repo = ChunkRepository(db)

    col = col_repo.get(collection_id, organization_id)
    if col is None:
        raise NotFoundError("Collection not found")

    # Collect document IDs in this collection before deletion
    docs, _ = doc_repo.list(
        organization_id=organization_id,
        collection_id=collection_id,
        limit=10000,
    )

    # Unlink documents from this collection
    for doc in docs:
        doc_repo.update(doc, collection_id=None)

    # Delete all chunks associated with this collection
    total_chunks_deleted = 0
    for doc in docs:
        deleted = chunk_repo.delete_by_document(doc.id, organization_id)
        total_chunks_deleted += deleted

    # Also try to delete chunks that directly reference this collection_id
    # (in case chunks were created with collection_id before document unlinking)
    try:
        from sqlalchemy import delete as sql_delete

        from app.knowledge.models.chunk import DocumentChunk

        stmt = sql_delete(DocumentChunk).where(
            DocumentChunk.collection_id == collection_id,
            DocumentChunk.organization_id == organization_id,
        )
        result = db.execute(stmt)
        total_chunks_deleted += result.rowcount
        db.commit()
    except Exception:
        pass

    # Hard delete the collection
    col_repo.delete(col)

    # Audit log
    try:
        platform = PlatformAdmin()
        platform.audit.append(
            "collection_deleted",
            "collection",
            collection_id,
            actor_id=user_id or None,
            organization_id=organization_id,
            details={
                "name": col.name,
                "documents_unlinked": len(docs),
                "chunks_deleted": total_chunks_deleted,
            },
        )
    except Exception:
        pass

    # Record metrics
    try:
        platform.metrics.record(
            "knowledge_collection_deleted",
            1.0,
            labels={"organization_id": organization_id},
        )
    except Exception:
        pass

    return None
