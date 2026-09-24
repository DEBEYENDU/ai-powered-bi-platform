from __future__ import annotations
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.iam.models.tenant import TenantApiKey

log = get_logger(__name__)


class ApiKeyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_key(self, organization_id: str, name: str, scopes: str = "*", expires_in_days: int | None = None, created_by: str | None = None) -> dict[str, Any]:
        raw_key = f"sk_{secrets.token_hex(24)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:12]

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = TenantApiKey(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            status="active",
            scopes=scopes,
            created_by=created_by,
            expires_at=expires_at,
        )
        self.db.add(api_key)
        self.db.commit()

        log.info("api_key_created", org_id=organization_id, name=name)
        return {"id": api_key.id, "key": raw_key, "key_prefix": key_prefix, "name": name, "scopes": scopes, "expires_at": expires_at.isoformat() if expires_at else None}

    def authenticate(self, raw_key: str) -> dict[str, Any] | None:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = self.db.query(TenantApiKey).filter(
            TenantApiKey.key_hash == key_hash,
            TenantApiKey.status == "active",
        ).first()

        if not api_key:
            return None

        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            api_key.status = "expired"
            self.db.commit()
            return None

        api_key.last_used_at = datetime.utcnow()
        self.db.commit()

        return {
            "organization_id": api_key.organization_id,
            "key_id": api_key.id,
            "name": api_key.name,
            "scopes": (api_key.scopes or "*").split(","),
        }

    def list_keys(self, organization_id: str) -> list[dict[str, Any]]:
        keys = self.db.query(TenantApiKey).filter(
            TenantApiKey.organization_id == organization_id,
        ).order_by(TenantApiKey.created_at.desc()).all()
        return [
            {
                "id": k.id, "name": k.name, "key_prefix": k.key_prefix,
                "status": k.status, "scopes": k.scopes or "*",
                "created_at": k.created_at.isoformat(),
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            }
            for k in keys
        ]

    def revoke_key(self, organization_id: str, key_id: str) -> bool:
        key = self.db.query(TenantApiKey).filter(
            TenantApiKey.id == key_id,
            TenantApiKey.organization_id == organization_id,
        ).first()
        if not key:
            return False
        key.status = "revoked"
        self.db.commit()
        log.info("api_key_revoked", org_id=organization_id, key_id=key_id)
        return True

    def rotate_key(self, organization_id: str, key_id: str) -> dict[str, Any] | None:
        key = self.db.query(TenantApiKey).filter(
            TenantApiKey.id == key_id,
            TenantApiKey.organization_id == organization_id,
        ).first()
        if not key:
            return None
        key.status = "revoked"
        self.db.commit()
        return self.create_key(organization_id, key.name, key.scopes or "*", created_by=key.created_by)
