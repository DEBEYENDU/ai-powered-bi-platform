from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.knowledge.models.document import DocumentStatus, KnowledgeDocument


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, doc: KnowledgeDocument) -> KnowledgeDocument:
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get(self, doc_id: str, organization_id: str) -> KnowledgeDocument | None:
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.status != DocumentStatus.DELETED,
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def list(
        self,
        organization_id: str,
        collection_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[KnowledgeDocument], int]:
        base_filter = [
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.status != DocumentStatus.DELETED,
        ]

        if collection_id is not None:
            base_filter.append(KnowledgeDocument.collection_id == collection_id)
        if status is not None:
            base_filter.append(KnowledgeDocument.status == status)

        count_stmt = select(func.count()).select_from(KnowledgeDocument).where(*base_filter)
        total = self.db.execute(count_stmt).scalar_one()

        stmt = (
            select(KnowledgeDocument)
            .where(*base_filter)
            .order_by(KnowledgeDocument.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = self.db.execute(stmt)
        docs = list(result.scalars().all())

        return docs, total

    def update(self, doc: KnowledgeDocument, **kwargs) -> KnowledgeDocument:
        for key, value in kwargs.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        doc.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def soft_delete(self, doc: KnowledgeDocument) -> KnowledgeDocument:
        doc.status = DocumentStatus.DELETED
        doc.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_by_checksum(self, organization_id: str, checksum: str) -> KnowledgeDocument | None:
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.checksum == checksum,
            KnowledgeDocument.status != DocumentStatus.DELETED,
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def count_by_status(self, organization_id: str) -> dict[str, int]:
        stmt = (
            select(KnowledgeDocument.status, func.count())
            .where(
                KnowledgeDocument.organization_id == organization_id,
                KnowledgeDocument.status != DocumentStatus.DELETED,
            )
            .group_by(KnowledgeDocument.status)
        )
        result = self.db.execute(stmt)
        counts: dict[str, int] = {}
        for status, count in result.all():
            counts[status] = count
        return counts

    def reindex(self, doc: KnowledgeDocument) -> KnowledgeDocument:
        doc.status = DocumentStatus.PROCESSING
        doc.error_message = None
        doc.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(doc)
        return doc
