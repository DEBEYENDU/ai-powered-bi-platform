"""Authentication router: login, register, token refresh."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.admin.services.platform import PlatformAdmin, get_platform
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.iam.schemas.user import TokenResponse, UserCreate, UserLogin

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(
    data: UserCreate, platform: PlatformAdmin = Depends(get_platform)
):
    try:
        user = platform.users.create(
            data.email, data.password, data.full_name or "", data.organization_id, ""
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"message": "registered", "user_id": user["id"]}


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin, platform: PlatformAdmin = Depends(get_platform)
):
    merged = platform.users._merged()
    user = None
    for u in merged.values():
        if u["email"] == data.email:
            user = u
            break
    if user is None or not verify_password(data.password, user.get("password_hash", "")):
        raise HTTPException(401, "Invalid email or password")
    if not user.get("is_active"):
        raise HTTPException(403, "Account is deactivated")
    roles = [r["name"] for r in platform.rbac.user_roles(user["id"])]
    token_data: dict = {"sub": user["id"]}
    if user.get("organization_id"):
        token_data["organization_id"] = user["organization_id"]
    if roles:
        token_data["roles"] = roles
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": user["id"]})
    platform.users.record_login(user["id"], True)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    token: str, platform: PlatformAdmin = Depends(get_platform)
):
    try:
        payload = decode_token(token)
    except Exception:  # noqa: BLE001 -- decode_token raises on invalid token
        raise HTTPException(401, "Invalid or expired refresh token") from None
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Not a refresh token")
    user = platform.users.get(payload.get("sub", ""))
    if user is None or not user.get("is_active"):
        raise HTTPException(403, "Account is deactivated")
    roles = [r["name"] for r in platform.rbac.user_roles(user["id"])]
    token_data: dict = {"sub": user["id"]}
    if user.get("organization_id"):
        token_data["organization_id"] = user["organization_id"]
    if roles:
        token_data["roles"] = roles
    access_token = create_access_token(token_data)
    new_refresh = create_refresh_token({"sub": user["id"]})
    return TokenResponse(access_token=access_token, refresh_token=new_refresh)
