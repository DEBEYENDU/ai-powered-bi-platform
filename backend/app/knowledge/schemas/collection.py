from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    access_policy: str = "organization"


class CollectionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    access_policy: str | None = None


class CollectionResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None
    access_policy: str
    created_by: str | None
    created_at: str
    updated_at: str | None
    document_count: int
    total_chunks: int

    model_config = {"from_attributes": True}


class CollectionListResponse(BaseModel):
    data: list[CollectionResponse]
    total: int
