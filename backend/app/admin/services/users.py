"""User administration: lifecycle, sessions, API keys, login history.

Operates on the IAM ``User`` model via injected accessors so this module never
duplicates auth logic — it only adds administrative operations (suspend,
force-reset, sessions, keys) around it.

Persistence: every mutation is mirrored to PostgreSQL via
``app.admin.repositories.db_store`` when the database is reachable
(DB is source of truth); the in-memory mirror keeps the service working
without a database and makes reads fast. No API changes were needed.
"""

from __future__ import annotations

import contextlib
import hashlib
import secrets
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.admin.repositories import db_store


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

    # -- merged view (DB wins, memory fills gaps) --
    def _merged(self) -> dict[str, dict[str, Any]]:
        merged = dict(self._users)
        rows = None
        with contextlib.suppress(Exception):
            rows = db_store.user_list_db()
        if rows:
            for row in rows:
                uid = row["id"]
                merged[uid] = {
                    **merged.get(uid, {}),
                    **{k: v for k, v in row.items() if v is not None},
                }
        return merged

    # -- lifecycle --
    def create(
        self,
        email: str,
        password: str,
        full_name: str = "",
        organization_id: str = "",
        username: str = "",
    ) -> dict[str, Any]:
        merged = self._merged()
        if any(u["email"] == email for u in merged.values()):
            raise ValueError("Email already exists")
        if username and any(u.get("username") == username for u in merged.values()):
            raise ValueError("Username already exists")
        uid = str(uuid4())
        user = {
            "id": uid,
            "email": email,
            "username": username or None,
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
        with contextlib.suppress(Exception):
            db_store.user_upsert(user)
        return self._public(user)

    def get(self, user_id: str) -> dict[str, Any] | None:
        row = None
        with contextlib.suppress(Exception):
            row = db_store.user_fetch(user_id)
        user = row or self._users.get(user_id)
        if user is not None:
            self._users[user_id] = {**self._users.get(user_id, {}), **user}
        return self._public(user) if user else None

    def update(self, user_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        user = self._merged().get(user_id)
        if user is None:
            return None
        if patch.get("email") and any(
            u["email"] == patch["email"] and u["id"] != user_id for u in self._merged().values()
        ):
            raise ValueError("Email already exists")
        for key in (
            "full_name",
            "username",
            "email",
            "organization_id",
            "is_verified",
            "mfa_enabled",
        ):
            if key in patch:
                user[key] = patch[key]
        self._users[user_id] = user
        with contextlib.suppress(Exception):
            db_store.user_upsert(user)
        return self._public(user)

    def set_active(self, user_id: str, active: bool) -> dict[str, Any] | None:
        user = self._merged().get(user_id)
        if user is None:
            return None
        user["is_active"] = active
        self._users[user_id] = user
        with contextlib.suppress(Exception):
            db_store.user_upsert(user)
        return self._public(user)

    def suspend(self, user_id: str, suspended: bool = True) -> dict[str, Any] | None:
        user = self._merged().get(user_id)
        if user is None:
            return None
        user["suspended"] = suspended
        if suspended:
            for session in self._sessions.values():
                if session["user_id"] == user_id:
                    session["revoked"] = True
                    with contextlib.suppress(Exception):
                        db_store.session_revoke_db(session["id"])
        self._users[user_id] = user
        with contextlib.suppress(Exception):
            db_store.user_upsert(user)
        return self._public(user)

    def delete(self, user_id: str) -> bool:
        user = self._merged().get(user_id)
        if user is None:
            return False
        user["is_active"] = False
        user["deleted"] = True
        self._users[user_id] = user
        with contextlib.suppress(Exception):
            db_store.user_upsert({**user, "is_active": False})
        return True

    def restore(self, user_id: str) -> dict[str, Any] | None:
        user = self._merged().get(user_id)
        if user is None:
            return None
        user.pop("deleted", None)
        user["is_active"] = True
        self._users[user_id] = user
        with contextlib.suppress(Exception):
            db_store.user_upsert(user)
        return self._public(user)

    def reset_password(self, user_id: str, new_password: str, force_change: bool = False) -> bool:
        user = self._merged().get(user_id)
        if user is None:
            return False
        user["password_hash"] = self._hash(new_password)
        user["force_password_reset"] = force_change
        self._users[user_id] = user
        with contextlib.suppress(Exception):
            db_store.user_upsert(user)
        return True

    def list(
        self, organization_id: str | None = None, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        users = list(self._merged().values())
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
        with contextlib.suppress(Exception):
            db_store.session_insert(session)
        return session

    def revoke_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session["revoked"] = True
        with contextlib.suppress(Exception):
            db_store.session_revoke_db(session_id)
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
        with contextlib.suppress(Exception):
            db_store.api_key_insert(record)
        return {**record, "api_key": raw}

    def revoke_api_key(self, key_id: str) -> bool:
        record = self._api_keys.get(key_id)
        if record is None:
            return False
        record["revoked"] = True
        with contextlib.suppress(Exception):
            db_store.api_key_revoke_db(key_id)
        return True

    def record_login(self, user_id: str, success: bool, ip_address: str = "") -> None:
        entry = {
            "user_id": user_id,
            "success": success,
            "ip_address": ip_address,
            "at": datetime.utcnow().isoformat(),
        }
        self._login_history.append(entry)
        with contextlib.suppress(Exception):
            db_store.login_insert(
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "success": success,
                    "ip_address": ip_address,
                }
            )
        user = self._users.get(user_id)
        if user and success:
            user["last_login_at"] = entry["at"]
            with contextlib.suppress(Exception):
                db_store.user_upsert(user)

    def login_history(self, user_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        rows = None
        with contextlib.suppress(Exception):
            rows = db_store.login_history_db(user_id, limit)
        if rows:
            return rows
        items = self._login_history
        if user_id:
            items = [h for h in items if h["user_id"] == user_id]
        return items[-limit:]

    @staticmethod
    def _public(user: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in user.items() if k != "password_hash"}
