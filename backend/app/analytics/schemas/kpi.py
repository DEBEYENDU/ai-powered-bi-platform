from datetime import datetime

from pydantic import BaseModel

from app.analytics.kpi.definitions import KPI


class KPICalculateRequest(BaseModel):
    kpi: KPI
    dataset_id: str
    start_date: str | None = None
    end_date: str | None = None


class KPICalculateResponse(BaseModel):
    kpi: KPI
    value: float
    unit: str
    timestamp: datetime
