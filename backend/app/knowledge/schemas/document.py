from enum import Enum

from pydantic import BaseModel


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETED = "deleted"


class DocumentCreate(BaseModel):
    filename: str
    content_type: str
    file_size: int
    title: str | None = None
    description: str | None = None
    collection_id: str | None = None
    source_type: str = "upload"
    source_url: str | None = None


class DocumentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    collection_id: str | None = None


class DocumentResponse(BaseModel):
    id: str
    organization_id: str
    collection_id: str | None
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    title: str | None
    description: str | None
    source_type: str
    status: str
    error_message: str | None
    created_by: str | None
    created_at: str
    updated_at: str | None
    indexed_at: str | None
    version: int
    chunk_count: int
    checksum: str

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    data: list[DocumentResponse]
    total: int
    page: int
    page_size: int
