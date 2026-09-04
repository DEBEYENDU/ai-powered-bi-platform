from fastapi import APIRouter

from app.iam.schemas.user import TokenResponse, UserCreate, UserLogin

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(data: UserCreate):
    # service call
    return {"message": "registered"}


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    return TokenResponse(access_token="...", refresh_token="...")  # noqa: S106 -- placeholder literals, not credentials
