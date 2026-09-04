"""Shared FastAPI dependencies: current user + organization scoping."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, Header

from app.core.security import decode_token
from app.exceptions.handlers import UnauthorizedError


def get_current_user(authorization: str | None = Header(None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
    except Exception:
        raise UnauthorizedError("Invalid or expired token") from None
    if payload.get("type") != "access":
        raise UnauthorizedError("Not an access token")
    return payload


def require_organization(
    organization_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> str:
    org = organization_id or user.get("org") or user.get("organization_id")
    if not org:
        raise UnauthorizedError("Organization context required")
    return str(org)
