from pydantic import BaseModel
from typing import Optional

class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None

class DatasetOut(BaseModel):
    id: str
    name: str
    status: str
    row_count: int
    file_size: int
    class Config:
        from_attributes = True
