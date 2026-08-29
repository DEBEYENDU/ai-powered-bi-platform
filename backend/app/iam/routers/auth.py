from fastapi import APIRouter, Depends
from app.iam.schemas.user import UserCreate, UserLogin, TokenResponse
from app.iam.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
async def register(data: UserCreate):
    # service call
    return {"message": "registered"}

@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    return TokenResponse(access_token="...", refresh_token="...")
