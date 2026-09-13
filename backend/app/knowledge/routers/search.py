"""Search endpoint for the Knowledge Base."""

from __future__ import annotations

import time

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.admin.services.platform import PlatformAdmin
from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization
from app.exceptions.handlers import AppError
from app.knowledge.repositories.chunk_repository import ChunkRepository
from app.knowledge.repositories.collection_repository import CollectionRepository
from app.knowledge.repositories.document_repository import DocumentRepository

search_router = APIRouter(prefix="/search", tags=["Knowledge Search"])


@search_router.post("")
async def search_knowledge(
    query: str = Body(...),
    collection_ids: list[str] | None = Body(None),
    top_k: int = Body(10),
    search_type: str = Body("hybrid"),
    min_score: float = Body(0.1),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Search the knowledge base using semantic, keyword, or hybrid retrieval.

    Search types:
    - **semantic**: Vector similarity search using embeddings
    - **keyword**: PostgreSQL full-text search using tsvector
    - **hybrid**: Combines semantic + keyword with configurable weights
    """
    start_time = time.time()

    if search_type not in ("semantic", "keyword", "hybrid"):
        raise AppError(
            f"Invalid search_type '{search_type}'. Must be one of: semantic, keyword, hybrid"
        )

    if top_k < 1 or top_k > 100:
        raise AppError("top_k must be between 1 and 100")

    chunk_repo = ChunkRepository(db)
    doc_repo = DocumentRepository(db)
    col_repo = CollectionRepository(db)

    # Resolve collection IDs to validate they belong to this org
    resolved_collection_ids: list[str] | None = None
    if collection_ids:
        resolved_collection_ids = []
        for cid in collection_ids:
            col = col_repo.get(cid, organization_id)
            if col is not None:
                resolved_collection_ids.append(cid)
        if not resolved_collection_ids:
            return {
                "query": query,
                "results": [],
                "total_results": 0,
                "search_type": search_type,
                "search_time_ms": round((time.time() - start_time) * 1000, 2),
            }

    results: list[dict] = []

    if search_type in ("semantic", "hybrid"):
        # Generate query embedding
        try:
            from app.ai.embeddings.manager import EmbeddingManager

            embedder = EmbeddingManager()
            embedder.initialize()
            query_embedding = embedder.get_embedding(query)
        except ImportError:
            query_embedding = None

        if query_embedding is not None:
            semantic_results = chunk_repo.search_by_embedding(
                org_id=organization_id,
                embedding=query_embedding,
                collection_ids=resolved_collection_ids,
                top_k=top_k * 2 if search_type == "hybrid" else top_k,
            )
            for chunk, score in semantic_results:
                if score < min_score:
                    continue
                results.append(
                    {
                        "chunk": chunk,
                        "score": score,
                        "source": "semantic",
                    }
                )

    if search_type in ("keyword", "hybrid"):
        keyword_results = chunk_repo.search_keyword(
            org_id=organization_id,
            query=query,
            collection_ids=resolved_collection_ids,
            top_k=top_k * 2 if search_type == "hybrid" else top_k,
        )
        for chunk in keyword_results:
            # Avoid duplicates from hybrid search
            already_found = any(r["chunk"].id == chunk.id for r in results)
            if already_found:
                continue
            # For keyword results without embedding scores, assign a reasonable score
            existing_scores = [r["score"] for r in results]
            keyword_score = 0.5 if not existing_scores else max(existing_scores) * 0.8
            results.append(
                {
                    "chunk": chunk,
                    "score": keyword_score,
                    "source": "keyword",
                }
            )

    # In hybrid mode, re-rank by combining scores
    if search_type == "hybrid":
        semantic_weight = 0.7
        keyword_weight = 0.3
        for r in results:
            if r["source"] == "semantic":
                r["score"] = semantic_weight * r["score"] + keyword_weight * 0.5
            else:
                r["score"] = keyword_weight * r["score"]

    # Sort by score descending and take top_k
    results.sort(key=lambda r: r["score"], reverse=True)
    results = results[:top_k]

    # Enrich results with document and collection info
    doc_cache: dict[str, any] = {}
    col_cache: dict[str, any] = {}

    search_results = []
    for r in results:
        chunk = r["chunk"]

        # Get document info (with caching)
        doc = doc_cache.get(chunk.document_id)
        if doc is None:
            doc = doc_repo.get(chunk.document_id, organization_id)
            doc_cache[chunk.document_id] = doc

        # Get collection info (with caching)
        col = None
        if chunk.collection_id:
            col = col_cache.get(chunk.collection_id)
            if col is None:
                col = col_repo.get(chunk.collection_id, organization_id)
                col_cache[chunk.collection_id] = col

        search_results.append(
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "document_title": doc.title if doc else None,
                "document_filename": doc.original_filename if doc else "unknown",
                "collection_id": chunk.collection_id,
                "collection_name": col.name if col else None,
                "text": chunk.text,
                "score": round(r["score"], 4),
                "page_number": chunk.page_number,
                "section": chunk.section,
                "highlighted": None,
            }
        )

    search_time_ms = round((time.time() - start_time) * 1000, 2)

    # Record metrics
    try:
        platform = PlatformAdmin()
        platform.metrics.record(
            "knowledge_search_performed",
            1.0,
            labels={
                "organization_id": organization_id,
                "search_type": search_type,
            },
        )
        platform.metrics.record(
            "knowledge_search_latency_ms",
            search_time_ms,
            labels={"search_type": search_type},
        )
    except Exception:
        pass

    return {
        "query": query,
        "results": search_results,
        "total_results": len(search_results),
        "search_type": search_type,
        "search_time_ms": search_time_ms,
    }
