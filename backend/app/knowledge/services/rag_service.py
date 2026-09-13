from __future__ import annotations

import re
import time

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.knowledge.repositories.chunk_repository import ChunkRepository
from app.knowledge.repositories.document_repository import DocumentRepository
from app.knowledge.schemas.answer import (
    CitationSource,
    ConfidenceMetadata,
    EvidenceStatus,
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.knowledge.services.embedding_service import EmbeddingService
from app.knowledge.services.retrieval_service import RetrievalService


class RAGService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.retrieval = RetrievalService(db)
        self.embedding_service = EmbeddingService()
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = ChunkRepository(db)

    async def query(self, request: RAGQueryRequest, org_id: str, user_id: str) -> RAGQueryResponse:
        start = time.time()

        retrieval_start = time.time()
        if request.search_type == "semantic":
            chunks = await self.retrieval.semantic_search(
                request.query, org_id, request.collection_ids, request.top_k
            )
        elif request.search_type == "keyword":
            chunks = self.retrieval.keyword_search(
                request.query, org_id, request.collection_ids, request.top_k
            )
        else:
            chunks = await self.retrieval.hybrid_search(
                request.query, org_id, request.collection_ids, request.top_k
            )
        retrieval_time = (time.time() - retrieval_start) * 1000

        sources = self._build_citation_sources(chunks)
        context = self._build_context(chunks, sources)

        generation_start = time.time()
        grounding_prompt = self._build_grounding_prompt(request.query, context)
        answer = await self._generate_answer(grounding_prompt)
        generation_time = (time.time() - generation_start) * 1000

        cleaned_answer, valid_sources = self._validate_citations(answer, sources)

        grounded = not self._detect_insufficient_evidence(cleaned_answer)
        evidence_status = self._determine_evidence_status(chunks, grounded)

        confidence = self._calculate_confidence(chunks, cleaned_answer)

        total_time = (time.time() - start) * 1000

        return RAGQueryResponse(
            query=request.query,
            answer=cleaned_answer,
            evidence_status=evidence_status.value,
            confidence=confidence,
            sources=valid_sources if request.include_sources else [],
            grounding_prompt_used=True,
            retrieval_time_ms=round(retrieval_time, 2),
            generation_time_ms=round(generation_time, 2),
            total_time_ms=round(total_time, 2),
        )

    def _build_citation_sources(self, chunks: list[dict]) -> list[CitationSource]:
        sources: list[CitationSource] = []
        for chunk in chunks:
            doc = self.doc_repo.get(chunk["document_id"], chunk.get("organization_id", ""))
            doc_title = doc.title if doc else "Unknown"
            doc_filename = doc.filename if doc else "unknown"

            sources.append(
                CitationSource(
                    document_id=chunk["document_id"],
                    document_title=doc_title,
                    document_filename=doc_filename,
                    chunk_id=chunk["chunk_id"],
                    page_number=chunk.get("page_number"),
                    section=chunk.get("section"),
                    text_excerpt=chunk["text"][:500],
                    relevance_score=chunk["score"],
                )
            )
        return sources

    def _build_context(self, chunks: list[dict], sources: list[CitationSource]) -> str:
        if not chunks:
            return "No relevant context found."

        context_parts: list[str] = []
        for i, (chunk, source) in enumerate(zip(chunks, sources), start=1):
            location = f"Page {source.page_number}" if source.page_number else "N/A"
            section = f", Section: {source.section}" if source.section else ""
            header = f"[Source {i}: {source.document_filename}, {location}{section}]"
            context_parts.append(f"{header}\n{chunk['text']}")

        return "\n\n---\n\n".join(context_parts)

    def _build_grounding_prompt(self, query: str, context: str) -> str:
        return f"""You are an enterprise knowledge assistant. Answer the user's question using ONLY the provided context documents.

CRITICAL RULES:
1. Use ONLY information from the provided context to answer.
2. If the context does not contain enough information to answer, say "I don't have enough information in the knowledge base to answer this question."
3. NEVER fabricate documents, page numbers, statistics, or citations.
4. Every claim must reference a specific source from the context.
5. If documents conflict, present both perspectives with their sources.
6. If you find the answer, cite it as [Source N] where N is the source number.

Available context:
{context}

User question: {query}

Answer:"""

    async def _generate_answer(self, prompt: str) -> str:
        settings = get_settings()

        if settings.openai_api_key:
            return await self._openai_generate(prompt)

        return (
            "I don't have enough information in the knowledge base to answer this question. "
            "No AI provider is configured for answer generation."
        )

    async def _openai_generate(self, prompt: str) -> str:
        settings = get_settings()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.openai_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.ai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": settings.ai_temperature,
                    "max_tokens": settings.ai_max_tokens,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _validate_citations(
        self, answer: str, sources: list[CitationSource]
    ) -> tuple[str, list[CitationSource]]:
        referenced = self.CitationValidator.extract_citations(answer)
        valid_indices = set(range(1, len(sources) + 1))
        valid_refs = [r for r in referenced if r in valid_indices]

        if not valid_refs:
            return answer, sources

        valid_sources = [sources[i - 1] for i in valid_refs if i - 1 < len(sources)]
        seen_ids: set[int] = set()
        deduped: list[CitationSource] = []
        for s in valid_sources:
            cid = id(s)
            if cid not in seen_ids:
                seen_ids.add(cid)
                deduped.append(s)

        cleaned = self.CitationValidator.remove_invalid_citations(answer, valid_indices)

        return cleaned, deduped

    def _calculate_confidence(self, chunks: list[dict], answer: str) -> ConfidenceMetadata:
        if not chunks:
            return ConfidenceMetadata(
                confidence=0.0,
                evidence_count=0,
                grounded=False,
                evidence_status=EvidenceStatus.INSUFFICIENT_EVIDENCE.value,
            )

        scores = [c.get("score", 0.0) for c in chunks]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        evidence_count = len(chunks)

        grounded = not self._detect_insufficient_evidence(answer)

        if not grounded:
            confidence = min(avg_score * 0.5, 0.3)
            status = EvidenceStatus.INSUFFICIENT_EVIDENCE
        elif self._detect_conflicting_evidence(chunks):
            confidence = avg_score * 0.7
            status = EvidenceStatus.CONFLICTING_EVIDENCE
        else:
            count_bonus = min(evidence_count / 5.0, 1.0)
            confidence = min(avg_score * 0.6 + count_bonus * 0.4, 1.0)
            status = EvidenceStatus.SUPPORTED

        return ConfidenceMetadata(
            confidence=round(confidence, 3),
            evidence_count=evidence_count,
            grounded=grounded,
            evidence_status=status.value,
        )

    def _detect_conflicting_evidence(self, chunks: list[dict]) -> bool:
        if len(chunks) < 2:
            return False

        number_pattern = re.compile(r"\b\d+(?:\.\d+)?%?\b")
        numbers_per_chunk = []
        for chunk in chunks:
            nums = set(number_pattern.findall(chunk["text"]))
            numbers_per_chunk.append(nums)

        for i in range(len(numbers_per_chunk)):
            for j in range(i + 1, len(numbers_per_chunk)):
                nums_i = numbers_per_chunk[i]
                nums_j = numbers_per_chunk[j]
                if nums_i and nums_j:
                    overlap = nums_i & nums_j
                    if not overlap and len(nums_i) > 0 and len(nums_j) > 0:
                        return True

        return False

    def _detect_insufficient_evidence(self, answer: str) -> bool:
        indicators = [
            "don't have enough information",
            "not enough information",
            "cannot answer",
            "no relevant",
            "insufficient",
            "unable to find",
            "no information available",
        ]
        return any(ind.lower() in answer.lower() for ind in indicators)

    def _determine_evidence_status(self, chunks: list[dict], grounded: bool) -> EvidenceStatus:
        if not grounded:
            return EvidenceStatus.INSUFFICIENT_EVIDENCE
        if self._detect_conflicting_evidence(chunks):
            return EvidenceStatus.CONFLICTING_EVIDENCE
        return EvidenceStatus.SUPPORTED

    class CitationValidator:
        @staticmethod
        def validate_answer(
            answer: str, sources: list[CitationSource]
        ) -> tuple[str, list[CitationSource], list[str]]:
            warnings: list[str] = []
            referenced = RAGService.CitationValidator.extract_citations(answer)

            valid_indices = set(range(1, len(sources) + 1))
            invalid_refs = [r for r in referenced if r not in valid_indices]

            for ref in invalid_refs:
                warnings.append(f"Citation [Source {ref}] references non-existent source")

            cleaned = RAGService.CitationValidator.remove_invalid_citations(answer, valid_indices)

            valid_sources = [sources[i - 1] for i in referenced if i in valid_indices]
            valid_sources = list(dict.fromkeys(valid_sources))

            return cleaned, valid_sources, warnings

        @staticmethod
        def extract_citations(answer: str) -> list[int]:
            pattern = r"\[Source\s+(\d+)\]"
            matches = re.findall(pattern, answer)
            return [int(m) for m in matches]

        @staticmethod
        def remove_invalid_citations(answer: str, valid_indices: set[int]) -> str:
            def _replace(match: re.Match) -> str:
                n = int(match.group(1))
                return match.group(0) if n in valid_indices else ""

            return re.sub(r"\[Source\s+(\d+)\]", _replace, answer)
