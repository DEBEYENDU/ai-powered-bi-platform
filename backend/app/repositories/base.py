"""Shared repository base: CRUD, pagination, filtering, soft delete.

Works with any SQLAlchemy model following the project conventions
(UUID ``id`` PK, optional ``deleted_at``). Concrete repos (e.g.
``iam/repositories/user_repo.py``) can subclass this instead of
reimplementing data access.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    def __init__(self, model: type[ModelT], db: Session):
        self.model = model
        self.db = db

    def get(self, id: UUID) -> ModelT | None:
        return self.db.get(self.model, id)

    def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> list[ModelT]:
        stmt = select(self.model)
        for key, value in (filters or {}).items():
            column = getattr(self.model, key, None)
            if column is not None:
                stmt = stmt.where(column == value)
        if not include_deleted and hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        stmt = stmt.limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all())

    def create(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: ModelT, patch: dict) -> ModelT:
        for key, value in patch.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        if hasattr(obj, "updated_at"):
            obj.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def soft_delete(self, obj: ModelT) -> ModelT:
        if hasattr(obj, "deleted_at"):
            obj.deleted_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(obj)
        else:  # pragma: no cover - models without soft delete
            self.db.delete(obj)
            self.db.commit()
        return obj
