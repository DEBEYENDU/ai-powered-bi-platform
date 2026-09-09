"""NLQ (Natural Language Query) schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NLQQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question about the data")
    include_chart: bool = Field(True, description="Include chart recommendation")
    temperature: float = Field(0.1, ge=0, le=2, description="LLM temperature")


class NLQExplainRequest(BaseModel):
    sql: str = Field(..., min_length=1, description="SQL query to explain")
    temperature: float = Field(0.3, ge=0, le=2)


class NLQQueryResponse(BaseModel):
    success: bool
    question: str
    sql: str
    columns: list[str] = []
    rows: list[dict[str, Any]] = []
    row_count: int = 0
    truncated: bool = False
    execution_time_ms: float = 0
    explanation: str = ""
    chart_recommendation: dict[str, Any] | None = None
    error: str | None = None


class NLQExplainResponse(BaseModel):
    sql: str
    explanation: str
    error: str | None = None


class NLQSchemaTable(BaseModel):
    name: str
    columns: list[dict[str, Any]]
    primary_key: list[str]
    row_count_estimate: int | None = None


class NLQSchemaResponse(BaseModel):
    database: str
    tables: dict[str, NLQSchemaTable]
    relationships: list[dict[str, Any]]
