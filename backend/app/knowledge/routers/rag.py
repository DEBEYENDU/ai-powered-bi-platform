"""RAG query endpoint for the Knowledge Base."""

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

rag_router = APIRouter(prefix="/rag", tags=["Knowledge RAG"])


def _estimate_confidence(results: list[dict]) -> dict:
    """Estimate confidence and evidence status from retrieval results."""
    if not results:
        return {
            "confidence": 0.0,
            "evidence_count": 0,
            "grounded": False,
            "evidence_status": "insufficient_evidence",
        }

    scores = [r["score"] for r in results]
    avg_score = sum(scores) / len(scores)
    max_score = max(scores)
    evidence_count = len([s for s in scores if s > 0.3])

    # Confidence is a weighted combination of average score, max score, and evidence count
    confidence = min(1.0, (avg_score * 0.4 + max_score * 0.3 + min(evidence_count / 5, 1.0) * 0.3))

    # Determine evidence status
    if evidence_count >= 2 and avg_score > 0.4:
        evidence_status = "supported"
    elif evidence_count == 0:
        evidence_status = "insufficient_evidence"
    else:
        # Check for conflicting evidence: low variance in scores means consistent,
        # high variance might mean conflicting. Simple heuristic.
        if len(scores) >= 2:
            variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            if variance > 0.1 and evidence_count >= 2:
                evidence_status = "conflicting_evidence"
            else:
                evidence_status = "supported" if avg_score > 0.3 else "insufficient_evidence"
        else:
            evidence_status = "insufficient_evidence"

    return {
        "confidence": round(confidence, 4),
        "evidence_count": evidence_count,
        "grounded": evidence_count >= 1 and confidence > 0.2,
        "evidence_status": evidence_status,
    }


def _build_answer_from_context(query: str, contexts: list[dict]) -> str:
    """Build a grounded answer from retrieved contexts.

    When an LLM is available, this delegates to the generation service.
    Otherwise, it assembles the most relevant excerpts into a coherent response.
    """
    try:
        from app.core.config import get_settings

        settings = get_settings()

        # Try OpenAI-compatible generation
        if settings.openai_api_key:
            import httpx

            context_texts = []
            for ctx in contexts[:5]:
                source_label = ctx.get("document_title") or ctx.get("document_filename", "unknown")
                context_texts.append(
                    f"[Source: {source_label}, Score: {ctx.get('score', 0):.2f}]\n{ctx['text']}"
                )

            system_prompt = (
                "You are a helpful assistant that answers questions based on the provided "
                "knowledge base context. Always cite your sources. If the context does not "
                "contain enough information to answer the question, say so clearly. "
                "Be concise and accurate."
            )
            user_prompt = (
                "Context from knowledge base:\n\n"
                + "\n---\n".join(context_texts)
                + f"\n\nQuestion: {query}\n\n"
                "Provide a clear, grounded answer with source citations."
            )

            response = httpx.post(
                f"{settings.openai_base_url}/chat/completions",
                json={
                    "model": settings.ai_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1024,
                },
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                timeout=30.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
    except Exception:
        pass

    # Fallback: assemble answer from top contexts
    if not contexts:
        return (
            "I couldn't find relevant information in the knowledge base to answer "
            "this question. Please try rephrasing your query or check if the "
            "relevant documents have been uploaded and indexed."
        )

    parts = ["Based on the knowledge base, here is what I found:\n"]
    for i, ctx in enumerate(contexts[:3], 1):
        source_label = ctx.get("document_title") or ctx.get("document_filename", "Unknown")
        excerpt = ctx["text"][:500].strip()
        if len(ctx["text"]) > 500:
            excerpt += "..."
        parts.append(f"{i}. **{source_label}** (relevance: {ctx['score']:.0%})\n{excerpt}\n")

    if len(contexts) > 3:
        parts.append(f"\n({len(contexts) - 3} additional sources found but not shown above.)")

    return "\n".join(parts)


@rag_router.post("/query")
async def rag_query(
    query: str = Body(...),
    collection_ids: list[str] | None = Body(None),
    top_k: int = Body(8),
    search_type: str = Body("hybrid"),
    include_sources: bool = Body(True),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    """Ask a question and get a grounded answer from the knowledge base.

    Returns answer with validated citations, confidence metadata,
    and evidence status (supported/insufficient/conflicting).
    """
    total_start = time.time()

    if search_type not in ("semantic", "keyword", "hybrid"):
        raise AppError(
            f"Invalid search_type '{search_type}'. Must be one of: semantic, keyword, hybrid"
        )

    chunk_repo = ChunkRepository(db)
    doc_repo = DocumentRepository(db)
    col_repo = CollectionRepository(db)

    # Resolve collection IDs
    resolved_collection_ids: list[str] | None = None
    if collection_ids:
        resolved_collection_ids = []
        for cid in collection_ids:
            col = col_repo.get(cid, organization_id)
            if col is not None:
                resolved_collection_ids.append(cid)

    # ── Retrieval phase ──
    retrieval_start = time.time()
    results: list[dict] = []

    if search_type in ("semantic", "hybrid"):
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
                results.append({"chunk": chunk, "score": score, "source": "semantic"})

    if search_type in ("keyword", "hybrid"):
        keyword_results = chunk_repo.search_keyword(
            org_id=organization_id,
            query=query,
            collection_ids=resolved_collection_ids,
            top_k=top_k * 2 if search_type == "hybrid" else top_k,
        )
        for chunk in keyword_results:
            already_found = any(r["chunk"].id == chunk.id for r in results)
            if not already_found:
                results.append({"chunk": chunk, "score": 0.5, "source": "keyword"})

    # Re-rank hybrid results
    if search_type == "hybrid":
        for r in results:
            if r["source"] == "semantic":
                r["score"] = 0.7 * r["score"] + 0.3 * 0.5
            else:
                r["score"] = 0.3 * r["score"]

    results.sort(key=lambda r: r["score"], reverse=True)
    results = results[:top_k]

    retrieval_time_ms = round((time.time() - retrieval_start) * 1000, 2)

    # ── Enrich results ──
    doc_cache: dict[str, any] = {}
    col_cache: dict[str, any] = {}

    sources = []
    for r in results:
        chunk = r["chunk"]

        doc = doc_cache.get(chunk.document_id)
        if doc is None:
            doc = doc_repo.get(chunk.document_id, organization_id)
            doc_cache[chunk.document_id] = doc

        col = None
        if chunk.collection_id:
            col = col_cache.get(chunk.collection_id)
            if col is None:
                col = col_repo.get(chunk.collection_id, organization_id)
                col_cache[chunk.collection_id] = col

        sources.append(
            {
                "document_id": chunk.document_id,
                "document_title": doc.title if doc else None,
                "document_filename": doc.original_filename if doc else "unknown",
                "chunk_id": chunk.id,
                "page_number": chunk.page_number,
                "section": chunk.section,
                "text_excerpt": chunk.text[:500] if len(chunk.text) > 500 else chunk.text,
                "relevance_score": round(r["score"], 4),
            }
        )

    # ── Generation phase ──
    generation_start = time.time()
    answer = _build_answer_from_context(query, sources)
    generation_time_ms = round((time.time() - generation_start) * 1000, 2)

    # ── Confidence estimation ──
    confidence_meta = _estimate_confidence(sources)

    total_time_ms = round((time.time() - total_start) * 1000, 2)

    # ── Audit log ──
    user_id: str = user.get("sub") or user.get("user_id") or ""
    try:
        platform = PlatformAdmin()
        platform.audit.append(
            "rag_query",
            "rag",
            "",
            actor_id=user_id or None,
            organization_id=organization_id,
            details={
                "query": query[:200],
                "search_type": search_type,
                "evidence_status": confidence_meta["evidence_status"],
                "confidence": confidence_meta["confidence"],
                "source_count": len(sources),
            },
        )
    except Exception:
        pass

    # ── Metrics ──
    try:
        platform.metrics.record(
            "knowledge_rag_query",
            1.0,
            labels={
                "organization_id": organization_id,
                "search_type": search_type,
                "evidence_status": confidence_meta["evidence_status"],
            },
        )
        platform.metrics.record(
            "knowledge_rag_retrieval_ms",
            retrieval_time_ms,
            labels={"search_type": search_type},
        )
        platform.metrics.record(
            "knowledge_rag_generation_ms",
            generation_time_ms,
            labels={"search_type": search_type},
        )
        platform.metrics.record(
            "knowledge_rag_confidence",
            confidence_meta["confidence"],
            labels={"organization_id": organization_id},
        )
    except Exception:
        pass

    return {
        "query": query,
        "answer": answer,
        "evidence_status": confidence_meta["evidence_status"],
        "confidence": {
            "confidence": confidence_meta["confidence"],
            "evidence_count": confidence_meta["evidence_count"],
            "grounded": confidence_meta["grounded"],
            "evidence_status": confidence_meta["evidence_status"],
        },
        "sources": sources if include_sources else [],
        "grounding_prompt_used": confidence_meta["grounded"],
        "retrieval_time_ms": retrieval_time_ms,
        "generation_time_ms": generation_time_ms,
        "total_time_ms": total_time_ms,
    }
