"""Security utilities: password hashing + JWT.

- Passwords: bcrypt when installed, PBKDF2-SHA256 fallback otherwise.
  Hashes are self-describing (``$bcrypt$...`` vs ``$pbkdf2$...``) so
  ``verify_password`` works regardless of which backend produced the hash.
- Tokens: PyJWT (HS256). Matches the existing ``AuthService`` call convention:
  ``create_access_token({"sub": user.id})``.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from app.core.config import get_settings

_PBKDF2_ITERATIONS = 210_000


# --- passwords ---

def _bcrypt_available() -> bool:
    try:
        import bcrypt  # type: ignore  # noqa: F401
        return True
    except Exception:
        return False


def hash_password(password: str) -> str:
    if _bcrypt_available():
        import bcrypt  # type: ignore
        return "$bcrypt$" + bcrypt.hashpw(
            password.encode(), bcrypt.gensalt()).decode()
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS).hex()
    return f"$pbkdf2${_PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        if password_hash.startswith("$bcrypt$"):
            import bcrypt  # type: ignore
            return bcrypt.checkpw(
                password.encode(), password_hash[len("$bcrypt$"):].encode())
        if password_hash.startswith("$pbkdf2$"):
            _, _, iterations, salt, digest = password_hash.split("$")
            check = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt.encode(), int(iterations)).hex()
            return hmac.compare_digest(check, digest)
    except Exception:
        return False
    return False


# --- tokens ---

def _expiry(minutes: Optional[int] = None, days: Optional[int] = None) -> datetime:
    settings = get_settings()
    if days is not None:
        return datetime.now(timezone.utc) + timedelta(days=days)
    return datetime.now(timezone.utc) + timedelta(
        minutes=minutes if minutes is not None else settings.access_token_expire_minutes)


def _encode(payload: Dict[str, Any]) -> str:
    settings = get_settings()
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(data: Dict[str, Any],
                        expires_minutes: Optional[int] = None) -> str:
    payload = dict(data)
    payload.update({"exp": _expiry(minutes=expires_minutes), "type": "access"})
    return _encode(payload)


def create_refresh_token(data: Dict[str, Any],
                         expires_days: Optional[int] = None) -> str:
    settings = get_settings()
    days = expires_days if expires_days is not None else settings.refresh_token_expire_days
    payload = dict(data)
    payload.update({"exp": _expiry(days=days), "type": "refresh"})
    return _encode(payload)


def decode_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key,
                      algorithms=[settings.jwt_algorithm])
