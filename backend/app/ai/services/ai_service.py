"""AI Service - main service layer for AI Business Assistant."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4

from app.ai.orchestrator.orchestrator import Orchestrator
from app.ai.rag.rag_pipeline import RAGPipeline
from app.ai.memory.memory import ConversationMemory
from app.ai.prompts.prompt_manager import PromptManager
from app.ai.tools.registry import ToolRegistry
from app.ai.monitoring.observability import AIMonitor
from app.ai.governance.audit import AuditLogger
from app.ai.cache.caching import AICache


class AIService:
    """Main service layer for the AI Business Assistant."""

    def __init__(
        self,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        self.organization_id = organization_id
        self.user_id = user_id
        self.orchestrator = Orchestrator()
        self.rag_pipeline = RAGPipeline()
        self.memory = ConversationMemory()
        self.prompt_manager = PromptManager()
        self.tool_registry = ToolRegistry()
        self.monitor = AIMonitor()
        self.audit_logger = AuditLogger()
        self.cache = AICache()

    async def process_chat(
        self,
        message: str,
        conversation_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        result = await self.orchestrator.process_query(
            query=message,
            user_id=self.user_id,
            organization_id=self.organization_id,
        )
        return result

    async def index_knowledge(
        self,
        content: str,
        source: str,
        source_type: str = "document",
    ) -> int:
        return self.rag_pipeline.index_document(
            content=content,
            source=source,
            source_type=source_type,
        )

    async def get_conversation_history(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        messages = self.memory.get_session_history(limit=limit)
        return [m.dict() for m in messages]

    async def add_to_memory(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.memory.add_message(role=role, content=content, metadata=metadata)

    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        return self.monitor.get_dashboard()

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        return [e.dict() for e in self.audit_logger.get_entries()]
