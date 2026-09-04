from datetime import datetime

from fastapi import APIRouter

from app.analytics.schemas.kpi import KPICalculateRequest, KPICalculateResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/kpi/calculate", response_model=KPICalculateResponse)
async def calculate_kpi(req: KPICalculateRequest):
    # placeholder return
    return KPICalculateResponse(kpi=req.kpi, value=0.0, unit="", timestamp=datetime.utcnow())
