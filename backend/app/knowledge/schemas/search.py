from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    collection_ids: list[str] | None = None
    top_k: int = Field(default=10, ge=1, le=100)
    search_type: str = "hybrid"
    min_score: float = Field(default=0.1, ge=0.0, le=1.0)


class SearchChunkResult(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str | None
    document_filename: str
    collection_id: str | None
    collection_name: str | None
    text: str
    score: float
    page_number: int | None
    section: str | None
    highlighted: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchChunkResult]
    total_results: int
    search_type: str
    search_time_ms: float
