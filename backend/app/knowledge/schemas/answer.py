from enum import Enum

from pydantic import BaseModel, Field


class CitationSource(BaseModel):
    document_id: str
    document_title: str | None
    document_filename: str
    chunk_id: str
    page_number: int | None
    section: str | None
    text_excerpt: str
    relevance_score: float


class EvidenceStatus(str, Enum):
    SUPPORTED = "supported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"


class ConfidenceMetadata(BaseModel):
    confidence: float
    evidence_count: int
    grounded: bool
    evidence_status: str


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    collection_ids: list[str] | None = None
    top_k: int = Field(default=8, ge=1, le=50)
    search_type: str = "hybrid"
    include_sources: bool = True


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    evidence_status: str
    confidence: ConfidenceMetadata
    sources: list[CitationSource]
    grounding_prompt_used: bool
    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float
