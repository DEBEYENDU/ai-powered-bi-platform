from __future__ import annotations
from typing import Any
from fastapi import Header, HTTPException
from app.db.session import get_db
from app.iam.services.api_key_service import ApiKeyService


async def get_api_key_organization(x_api_key: str | None = Header(None)) -> dict[str, Any] | None:
    if not x_api_key:
        return None
    db = next(get_db())
    try:
        service = ApiKeyService(db)
        result = service.authenticate(x_api_key)
        if not result:
            raise HTTPException(status_code=401, detail="Invalid or expired API key")
        return result
    finally:
        db.close()
