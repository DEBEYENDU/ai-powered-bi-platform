from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.knowledge.models.collection import KnowledgeCollection


class CollectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, col: KnowledgeCollection) -> KnowledgeCollection:
        self.db.add(col)
        self.db.commit()
        self.db.refresh(col)
        return col

    def get(self, col_id: str, organization_id: str) -> KnowledgeCollection | None:
        stmt = select(KnowledgeCollection).where(
            KnowledgeCollection.id == col_id,
            KnowledgeCollection.organization_id == organization_id,
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def list(
        self, organization_id: str, limit: int = 50, offset: int = 0
    ) -> tuple[list[KnowledgeCollection], int]:
        count_stmt = (
            select(func.count())
            .select_from(KnowledgeCollection)
            .where(KnowledgeCollection.organization_id == organization_id)
        )
        total = self.db.execute(count_stmt).scalar_one()

        stmt = (
            select(KnowledgeCollection)
            .where(KnowledgeCollection.organization_id == organization_id)
            .order_by(KnowledgeCollection.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = self.db.execute(stmt)
        cols = list(result.scalars().all())

        return cols, total

    def update(self, col: KnowledgeCollection, **kwargs) -> KnowledgeCollection:
        for key, value in kwargs.items():
            if hasattr(col, key):
                setattr(col, key, value)
        col.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(col)
        return col

    def delete(self, col: KnowledgeCollection) -> None:
        self.db.delete(col)
        self.db.commit()

    def get_by_name(self, organization_id: str, name: str) -> KnowledgeCollection | None:
        stmt = select(KnowledgeCollection).where(
            KnowledgeCollection.organization_id == organization_id,
            KnowledgeCollection.name == name,
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def update_counts(self, col_id: str, doc_delta: int, chunk_delta: int) -> None:
        stmt = (
            update(KnowledgeCollection)
            .where(KnowledgeCollection.id == col_id)
            .values(
                document_count=KnowledgeCollection.document_count + doc_delta,
                total_chunks=KnowledgeCollection.total_chunks + chunk_delta,
                updated_at=datetime.utcnow(),
            )
        )
        self.db.execute(stmt)
        self.db.commit()
