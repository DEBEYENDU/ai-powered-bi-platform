"""Chat schemas (canonical home for conversation message types).

Re-exported from ``app.ai.tools.schemas`` where the Pydantic models live,
so both ``app.ai.schemas.chat`` and ``app.ai.tools.schemas`` resolve
to the same classes.
"""

from app.ai.tools.schemas import ChatMessage, ChatRequest, ChatResponse

__all__ = ["ChatMessage", "ChatRequest", "ChatResponse"]
