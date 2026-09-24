from datetime import datetime

from fastapi import APIRouter, Depends

from app.analytics.schemas.kpi import KPICalculateRequest, KPICalculateResponse
from app.dependencies.deps import get_current_user, require_organization

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/kpi/calculate", response_model=KPICalculateResponse)
async def calculate_kpi(
    req: KPICalculateRequest,
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    # placeholder return
    return KPICalculateResponse(kpi=req.kpi, value=0.0, unit="", timestamp=datetime.utcnow())
