"""AI Assistant FastAPI router - chat, conversations, providers."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.providers.registry import list_providers
from app.ai.schemas.chat import (
    ChatRequest,
    ConversationDetail,
    ConversationMessageOut,
    ConversationOut,
    ConversationUpdate,
)
from app.ai.services.chat_service import ChatService
from app.db.session import get_db
from app.dependencies.deps import get_current_user, require_organization

ai_router = APIRouter(prefix="/ai", tags=["AI Assistant"])


def _get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    return ChatService(db)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


@ai_router.post("/chat", response_model=dict[str, Any])
async def chat(
    request: ChatRequest = Body(...),
    service: ChatService = Depends(_get_chat_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
) -> dict[str, Any]:
    """Send a message and get a response (non-streaming or streaming via SSE)."""
    # Resolve or create conversation
    conv_id = request.conversation_id
    if conv_id:
        conv = service.get_conversation(conv_id, organization_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conv = service.create_conversation(
            model=request.model,
            provider=request.provider,
            system_prompt=request.system_prompt,
            user_id=user.get("sub"),
            organization_id=organization_id,
        )
        conv_id = conv.id

    if request.stream:
        return StreamingResponse(
            _stream_response(service, conv_id, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    result = await service.send_message(
        conversation_id=conv_id,
        message=request.message,
        model=request.model,
        provider_name=request.provider,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        system_prompt=request.system_prompt,
    )
    return result


async def _stream_response(service: ChatService, conv_id: str, request: ChatRequest):
    """Generate SSE events from streaming response."""
    try:
        async for chunk in service.send_message_stream(
            conversation_id=conv_id,
            message=request.message,
            model=request.model,
            provider_name=request.provider,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            system_prompt=request.system_prompt,
        ):
            event_data = {
                "delta": chunk.delta,
                "conversation_id": conv_id,
                "finish_reason": chunk.finish_reason,
            }
            if chunk.usage:
                event_data["usage"] = chunk.usage
            yield f"data: {json.dumps(event_data)}\n\n"
    except ValueError:
        yield f"data: {json.dumps({'error': 'Invalid request parameters'})}\n\n"
    except Exception:  # noqa: BLE001
        yield f"data: {json.dumps({'error': 'An unexpected error occurred'})}\n\n"
    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Conversations CRUD
# ---------------------------------------------------------------------------


@ai_router.get("/conversations", response_model=dict[str, Any])
async def list_conversations(
    user_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: ChatService = Depends(_get_chat_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    conversations = service.list_conversations(
        user_id=user_id, limit=limit, offset=offset, organization_id=organization_id
    )
    total = service.count_conversations(user_id=user_id, organization_id=organization_id)
    return {
        "data": [ConversationOut.model_validate(c).model_dump() for c in conversations],
        "total": total,
    }


@ai_router.post("/conversations", response_model=dict[str, Any])
async def create_conversation(
    title: str = Body("New conversation"),
    model: str | None = Body(None),
    provider: str | None = Body(None),
    system_prompt: str | None = Body(None),
    service: ChatService = Depends(_get_chat_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    conv = service.create_conversation(
        title=title,
        model=model,
        provider=provider,
        system_prompt=system_prompt,
        user_id=user.get("sub"),
        organization_id=organization_id,
    )
    return ConversationOut.model_validate(conv).model_dump()


@ai_router.get("/conversations/{conversation_id}", response_model=dict[str, Any])
async def get_conversation(
    conversation_id: str,
    service: ChatService = Depends(_get_chat_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    conv = service.get_conversation(conversation_id, organization_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = service.get_messages(conversation_id)
    data = ConversationDetail.model_validate(conv).model_dump()
    data["messages"] = [ConversationMessageOut.model_validate(m).model_dump() for m in messages]
    return data


@ai_router.patch("/conversations/{conversation_id}", response_model=dict[str, Any])
async def update_conversation(
    conversation_id: str,
    update: ConversationUpdate = Body(...),
    service: ChatService = Depends(_get_chat_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    conv = service.update_conversation(
        conversation_id,
        title=update.title,
        model=update.model,
        provider=update.provider,
        system_prompt=update.system_prompt,
        organization_id=organization_id,
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationOut.model_validate(conv).model_dump()


@ai_router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    service: ChatService = Depends(_get_chat_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    if not service.delete_conversation(conversation_id, organization_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Conversation messages
# ---------------------------------------------------------------------------


@ai_router.get("/conversations/{conversation_id}/messages", response_model=list[dict[str, Any]])
async def get_messages(
    conversation_id: str,
    limit: int = Query(100, ge=1, le=500),
    service: ChatService = Depends(_get_chat_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    conv = service.get_conversation(conversation_id, organization_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = service.get_messages(conversation_id, limit=limit)
    return [ConversationMessageOut.model_validate(m).model_dump() for m in messages]


# ---------------------------------------------------------------------------
# Providers & health
# ---------------------------------------------------------------------------


@ai_router.get("/providers", response_model=list[dict[str, Any]])
async def get_providers(
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    return list_providers()


@ai_router.get("/health", response_model=dict[str, Any])
async def get_ai_health(
    service: ChatService = Depends(_get_chat_service),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    providers = list_providers()
    return {
        "status": "healthy",
        "providers": providers,
        "active_provider": service._default_provider_name(),
        "active_model": service._default_model(),
    }


# ---------------------------------------------------------------------------
# Suggested questions (legacy compat)
# ---------------------------------------------------------------------------


@ai_router.get("/suggested-questions")
async def get_suggested_questions(
    topic: str | None = Query(None),
    user: dict = Depends(get_current_user),
    organization_id: str = Depends(require_organization),
):
    return {
        "questions": [
            "What are my top KPIs this month?",
            "Show me revenue trends",
            "What products have the highest profit?",
            "Forecast next quarter's sales",
        ]
    }
