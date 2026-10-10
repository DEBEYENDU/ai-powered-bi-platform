"""Authentication router: login, register, token refresh."""

from __future__ import annotations

import contextlib
import re
import uuid as uuidlib

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.admin.services.platform import PlatformAdmin, get_platform
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.iam.schemas.user import TokenResponse, UserCreate, UserLogin

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:40] or "tenant"


@router.post("/register")
async def register(
    data: UserCreate, platform: PlatformAdmin = Depends(get_platform)
):
    organization_id = (data.organization_id or "").strip()
    try:
        user = platform.users.create(
            data.email, data.password, data.full_name or "", organization_id, ""
        )
    except ValueError as exc:
        msg = str(exc)
        if "Email already exists" in msg:
            raise HTTPException(409, "An account with this email already exists. Please sign in.") from exc
        raise HTTPException(400, msg) from exc

    if not organization_id:
        # Self-signup: provision a dedicated tenant for this user after user creation succeeded.
        from app.db.session import get_engine
        from app.iam.services.provisioning_service import ProvisioningService

        base = _slugify(data.full_name or data.email.split("@")[0])
        slug = f"{base}-{uuidlib.uuid4().hex[:6]}"
        # organizations.owner_id has a FK to iam.users: only claim ownership
        # when the user row really exists in SQL (db_store can silently fall
        # back to memory-only mode), otherwise provisioning would be rejected.
        owner_id: str | None = None
        with contextlib.suppress(Exception):
            from app.admin.repositories import db_store

            owner_id = user["id"] if db_store.user_fetch(user["id"]) else None
        try:
            with Session(get_engine()) as db:
                result = ProvisioningService(db).provision_tenant(
                    name=data.full_name or data.email.split("@")[0],
                    slug=slug,
                    plan_name="free",
                    trial_days=14,
                    owner_id=owner_id,
                )
            organization_id = result.get("organization_id", "")
        except Exception as exc:  # noqa: BLE001
            from app.core.logging import get_logger
            get_logger(__name__).error("register_provisioning_failed", error=str(exc))
            # Cleanup user if tenant provisioning fails to avoid orphan users
            with contextlib.suppress(Exception):
                platform.users.delete(user["id"])
            raise HTTPException(503, "Tenant provisioning failed; try again") from None
        if not organization_id:
            with contextlib.suppress(Exception):
                platform.users.delete(user["id"])
            raise HTTPException(503, "Tenant provisioning failed; try again")
        # Link user to newly provisioned organization
        with contextlib.suppress(Exception):
            platform.users.update(user["id"], {"organization_id": organization_id})
    # Verify the user actually persisted — never return a fake success.
    persisted = platform.users.get(user["id"])
    if persisted is None or persisted.get("email") != data.email:
        from app.core.logging import get_logger

        get_logger(__name__).error("register_persistence_failed", user_id=user["id"])
        raise HTTPException(503, "Registration could not be persisted; try again")
    # Tenant owners administer their own organization.
    with contextlib.suppress(Exception):
        platform.rbac.assign_role(user["id"], "sys-org_admin")
    return {
        "message": "registered",
        "user_id": user["id"],
        "organization_id": organization_id,
    }


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
    token: str = Body(..., embed=True), platform: PlatformAdmin = Depends(get_platform)
):
    """Exchange a refresh token for a new token pair.

    The token travels in the request body — never in the URL, where it would
    end up in server access logs, proxies and browser history.
    """
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
