from pydantic import BaseModel
from typing import Optional
from analytics.kpi.definitions import KPI

class KPICalculateRequest(BaseModel):
    kpi: KPI
    dataset_id: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class KPICalculateResponse(BaseModel):
    kpi: KPI
    value: float
    unit: str
    timestamp: datetime