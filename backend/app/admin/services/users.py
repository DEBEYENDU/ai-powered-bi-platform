"""User administration: lifecycle, sessions, API keys, login history.

Operates on the IAM ``User`` model via injected accessors so this module never
duplicates auth logic — it only adds administrative operations (suspend,
force-reset, sessions, keys) around it.
"""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import uuid4


class UserAdminService:
    def __init__(
        self,
        user_store: dict[str, dict[str, Any]] | None = None,
        password_hasher: Callable[[str], str] | None = None,
    ) -> None:
        self._users: dict[str, dict[str, Any]] = user_store if user_store is not None else {}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._api_keys: dict[str, dict[str, Any]] = {}
        self._login_history: list[dict[str, Any]] = []
        self._hash = password_hasher or self._default_hash

    @staticmethod
    def _default_hash(password: str) -> str:
        try:
            from app.core.security import hash_password  # type: ignore

            return hash_password(password)
        except ImportError:
            return "sha256$" + hashlib.sha256(password.encode()).hexdigest()

    # -- lifecycle --
    def create(
        self, email: str, password: str, full_name: str = "", organization_id: str = ""
    ) -> dict[str, Any]:
        if any(u["email"] == email for u in self._users.values()):
            raise ValueError("Email already exists")
        uid = str(uuid4())
        user = {
            "id": uid,
            "email": email,
            "password_hash": self._hash(password),
            "full_name": full_name,
            "organization_id": organization_id,
            "is_active": True,
            "is_verified": False,
            "suspended": False,
            "mfa_enabled": False,
            "force_password_reset": False,
            "last_login_at": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._users[uid] = user
        return self._public(user)

    def get(self, user_id: str) -> dict[str, Any] | None:
        user = self._users.get(user_id)
        return self._public(user) if user else None

    def update(self, user_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        user = self._users.get(user_id)
        if user is None:
            return None
        for key in ("full_name", "organization_id", "is_verified", "mfa_enabled"):
            if key in patch:
                user[key] = patch[key]
        return self._public(user)

    def set_active(self, user_id: str, active: bool) -> dict[str, Any] | None:
        user = self._users.get(user_id)
        if user is None:
            return None
        user["is_active"] = active
        return self._public(user)

    def suspend(self, user_id: str, suspended: bool = True) -> dict[str, Any] | None:
        user = self._users.get(user_id)
        if user is None:
            return None
        user["suspended"] = suspended
        if suspended:
            for session in self._sessions.values():
                if session["user_id"] == user_id:
                    session["revoked"] = True
        return self._public(user)

    def delete(self, user_id: str) -> bool:
        user = self._users.get(user_id)
        if user is None:
            return False
        user["is_active"] = False
        user["deleted"] = True
        return True

    def restore(self, user_id: str) -> dict[str, Any] | None:
        user = self._users.get(user_id)
        if user is None:
            return None
        user.pop("deleted", None)
        user["is_active"] = True
        return self._public(user)

    def reset_password(self, user_id: str, new_password: str, force_change: bool = False) -> bool:
        user = self._users.get(user_id)
        if user is None:
            return False
        user["password_hash"] = self._hash(new_password)
        user["force_password_reset"] = force_change
        return True

    def list(
        self, organization_id: str | None = None, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        users = list(self._users.values())
        if organization_id:
            users = [u for u in users if u.get("organization_id") == organization_id]
        if not include_inactive:
            users = [u for u in users if u.get("is_active") and not u.get("deleted")]
        return [self._public(u) for u in users]

    # -- sessions / keys / history --
    def create_session(
        self, user_id: str, ip_address: str = "", user_agent: str = ""
    ) -> dict[str, Any]:
        sid = str(uuid4())
        session = {
            "id": sid,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "revoked": False,
            "last_seen_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
        }
        self._sessions[sid] = session
        return session

    def revoke_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session["revoked"] = True
        return True

    def sessions(self, user_id: str) -> list[dict[str, Any]]:
        return [s for s in self._sessions.values() if s["user_id"] == user_id]

    def create_api_key(self, user_id: str, name: str = "") -> dict[str, Any]:
        raw = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        record = {
            "id": str(uuid4()),
            "user_id": user_id,
            "name": name,
            "key_hash": key_hash,
            "key_prefix": raw[:8],
            "revoked": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._api_keys[record["id"]] = record
        return {**record, "api_key": raw}

    def revoke_api_key(self, key_id: str) -> bool:
        record = self._api_keys.get(key_id)
        if record is None:
            return False
        record["revoked"] = True
        return True

    def record_login(self, user_id: str, success: bool, ip_address: str = "") -> None:
        self._login_history.append(
            {
                "user_id": user_id,
                "success": success,
                "ip_address": ip_address,
                "at": datetime.utcnow().isoformat(),
            }
        )
        user = self._users.get(user_id)
        if user and success:
            user["last_login_at"] = datetime.utcnow().isoformat()

    def login_history(self, user_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        items = self._login_history
        if user_id:
            items = [h for h in items if h["user_id"] == user_id]
        return items[-limit:]

    @staticmethod
    def _public(user: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in user.items() if k != "password_hash"}
