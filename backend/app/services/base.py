"""Shared service-layer base: validation hooks, transactions, logging."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger


class ServiceError(Exception):
    """Domain error raised by services (mapped to 4xx by exception handlers)."""


class BaseService:
    def __init__(self, db: Session | None = None):
        self.db = db
        self.log = get_logger(type(self).__name__)

    def run_in_transaction(self, fn: Callable[[], Any]) -> Any:
        if self.db is None:
            return fn()
        try:
            result = fn()
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            raise ServiceError(message)
