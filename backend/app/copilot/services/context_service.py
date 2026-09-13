from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger

log = get_logger("copilot.context")


class ContextService:
    """Collects and organizes context for copilot requests."""

    def __init__(self, db: Session):
        self.db = db

    async def collect_context(
        self,
        user: dict[str, Any],
        organization_id: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Build the full context for a copilot request."""
        context: dict[str, Any] = {
            "user_id": user.get("sub") or user.get("user_id", ""),
            "organization_id": organization_id,
            "session_id": session_id,
        }

        try:
            from sqlalchemy import select

            from app.dataset.models.dataset import Dataset

            stmt = (
                select(Dataset)
                .where(
                    Dataset.organization_id == organization_id,
                    Dataset.deleted_at.is_(None),
                )
                .limit(20)
            )
            datasets = list(self.db.scalars(stmt).all())
            context["datasets"] = [
                {
                    "id": d.id,
                    "name": d.name,
                    "row_count": d.row_count,
                    "column_count": d.column_count,
                }
                for d in datasets
            ]
        except Exception:
            context["datasets"] = []

        try:
            from sqlalchemy import select

            from app.knowledge.models.collection import KnowledgeCollection

            stmt = (
                select(KnowledgeCollection)
                .where(
                    KnowledgeCollection.organization_id == organization_id,
                )
                .limit(20)
            )
            collections = list(self.db.scalars(stmt).all())
            context["knowledge_collections"] = [
                {"id": c.id, "name": c.name, "document_count": c.document_count}
                for c in collections
            ]
        except Exception:
            context["knowledge_collections"] = []

        try:
            from sqlalchemy import select

            from app.copilot.models.session import CopilotSession

            stmt = (
                select(CopilotSession)
                .where(
                    CopilotSession.organization_id == organization_id,
                    CopilotSession.user_id == context["user_id"],
                )
                .order_by(CopilotSession.created_at.desc())
                .limit(5)
            )
            sessions = list(self.db.scalars(stmt).all())
            context["recent_sessions"] = [
                {"id": s.id, "title": s.title, "created_at": str(s.created_at)} for s in sessions
            ]
        except Exception:
            context["recent_sessions"] = []

        return context
