from pydantic import BaseModel


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None
    category: str | None = None


class DatasetOut(BaseModel):
    id: str
    name: str
    status: str
    row_count: int
    file_size: int

    class Config:
        from_attributes = True
