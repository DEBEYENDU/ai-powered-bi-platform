"""Citation engine for AI Business Assistant."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.ai.schemas.citation import Citation, CitationResponse


class CitationEngine:
    """Generates citations for AI responses."""

    def __init__(self) -> None:
        self._citation_store: dict[str, list[Citation]] = {}

    async def generate(
        self,
        execution_results: list[Any],
        request_id: str,
    ) -> list[dict[str, Any]]:
        citations: list[Citation] = []

        for result in execution_results:
            if not result.success:
                continue
            data = result.data if hasattr(result, "data") and result.data else None
            if data is None:
                continue
            citation = self._build_citation(result.tool_name, data, request_id)
            if citation:
                citations.append(citation)

        self._citation_store[request_id] = citations
        return [c.dict() for c in citations]

    def _build_citation(
        self,
        tool_name: str,
        data: Any,
        request_id: str,
    ) -> Citation | None:
        snippet = self._extract_snippet(data)
        if not snippet:
            return None
        return Citation(
            source=tool_name,
            source_type="tool_result",
            source_id=uuid4(),
            snippet=snippet[:500],
            relevance_score=0.85,
            retrieved_at=datetime.utcnow(),
        )

    def _extract_snippet(self, data: Any) -> str | None:
        if isinstance(data, dict):
            if "summary" in data:
                return str(data["summary"])
            if "values" in data:
                return str(data["values"])
            return str({k: v for k, v in list(data.items())[:3]})
        if isinstance(data, str):
            return data[:500]
        return str(data)[:500]

    def get_citations(self, request_id: str) -> list[dict[str, Any]]:
        citations = self._citation_store.get(request_id, [])
        return [c.dict() for c in citations]

    def get_citation_response(
        self,
        claim: str,
        conversation_id: str,
    ) -> CitationResponse:
        citations = self._citation_store.get(conversation_id, [])
        evidence_strength = (
            "strong" if len(citations) > 3 else "moderate" if len(citations) > 1 else "weak"
        )
        confidence = min(1.0, len(citations) * 0.25)
        return CitationResponse(
            citations=citations,
            confidence_score=confidence,
            evidence_strength=evidence_strength,
        )
