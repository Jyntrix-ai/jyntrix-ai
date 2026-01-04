"""Chat routes with SSE streaming using sse-starlette."""

import json
import logging
from typing import Any, AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse

from src.dependencies import CurrentUser, QdrantDep, RedisDep, SupabaseAdminDep
from src.schemas.chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
    SendMessageRequest,
)
from src.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_chat_service(
    supabase: SupabaseAdminDep,
    qdrant: QdrantDep,
    redis: RedisDep,
) -> ChatService:
    """Get chat service instance."""
    return ChatService(supabase=supabase, qdrant=qdrant, redis=redis)


@router.post(
    "/send",
    response_class=EventSourceResponse,
    summary="Send message with SSE streaming",
    description="Send a message and receive streaming response via Server-Sent Events",
)
async def send_message_stream(
    request: SendMessageRequest,
    current_user: CurrentUser,
    chat_service: ChatService = Depends(get_chat_service),
) -> EventSourceResponse:
    """Send a message and stream the response using SSE."""

    async def event_generator() -> AsyncGenerator[dict[str, Any], None]:
        """Generate SSE events for the chat response."""
        try:
            # Start event
            yield {
                "event": "start",
                "data": json.dumps({
                    "type": "start",
                    "conversation_id": str(request.conversation_id) if request.conversation_id else None,
                }),
            }

            # Stream the response
            conversation_id = None
            message_id = None

            async for chunk in chat_service.send_message_stream(
                user_id=current_user.id,
                content=request.content,
                conversation_id=request.conversation_id,
                include_memory=request.include_memory,
            ):
                if chunk.get("type") == "metadata":
                    conversation_id = chunk.get("conversation_id")
                    message_id = chunk.get("message_id")
                    yield {
                        "event": "metadata",
                        "data": json.dumps(chunk),
                    }
                elif chunk.get("type") == "text":
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "text",
                            "content": chunk.get("content", ""),
                        }),
                    }
                elif chunk.get("type") == "error":
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "type": "error",
                            "error": chunk.get("error", "Unknown error"),
                        }),
                    }

            # Done event
            yield {
                "event": "done",
                "data": json.dumps({
                    "type": "done",
                    "conversation_id": str(conversation_id) if conversation_id else None,
                    "message_id": str(message_id) if message_id else None,
                }),
            }

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "type": "error",
                    "error": str(e),
                }),
            }

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/complete",
    response_model=ChatCompletionResponse,
    summary="Chat completion (non-streaming)",
    description="Send a message and receive complete response",
)
async def chat_completion(
    request: ChatCompletionRequest,
    current_user: CurrentUser,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatCompletionResponse:
    """Non-streaming chat completion."""
    try:
        result = await chat_service.complete(
            user_id=current_user.id,
            messages=request.messages,
            conversation_id=request.conversation_id,
            include_memory=request.include_memory,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        return result
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
    description="Create a new conversation, optionally with an initial message",
)
async def create_conversation(
    request: ConversationCreate,
    current_user: CurrentUser,
    chat_service: ChatService = Depends(get_chat_service),
) -> ConversationResponse:
    """Create a new conversation."""
    try:
        conversation = await chat_service.create_conversation(
            user_id=current_user.id,
            title=request.title,
            metadata=request.metadata,
            initial_message=request.initial_message,
        )
        return conversation
    except Exception as e:
        logger.error(f"Create conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List conversations",
    description="Get paginated list of user's conversations",
)
async def list_conversations(
    current_user: CurrentUser,
    chat_service: ChatService = Depends(get_chat_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    archived: bool = Query(default=False),
) -> ConversationListResponse:
    """List user's conversations."""
    try:
        result = await chat_service.list_conversations(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            archived=archived,
        )
        return result
    except Exception as e:
        logger.error(f"List conversations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation details",
    description="Get a conversation with all its messages",
)
async def get_conversation(
    conversation_id: UUID,
    current_user: CurrentUser,
    chat_service: ChatService = Depends(get_chat_service),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ConversationDetailResponse:
    """Get conversation with messages."""
    try:
        conversation = await chat_service.get_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Update conversation",
    description="Update conversation title or archive status",
)
async def update_conversation(
    conversation_id: UUID,
    request: ConversationUpdate,
    current_user: CurrentUser,
    chat_service: ChatService = Depends(get_chat_service),
) -> ConversationResponse:
    """Update a conversation."""
    try:
        conversation = await chat_service.update_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
            title=request.title,
            is_archived=request.is_archived,
            metadata=request.metadata,
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete conversation",
    description="Permanently delete a conversation and all its messages",
)
async def delete_conversation(
    conversation_id: UUID,
    current_user: CurrentUser,
    chat_service: ChatService = Depends(get_chat_service),
) -> Response:
    """Delete a conversation."""
    try:
        deleted = await chat_service.delete_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="Get conversation messages",
    description="Get paginated messages from a conversation",
)
async def get_messages(
    conversation_id: UUID,
    current_user: CurrentUser,
    chat_service: ChatService = Depends(get_chat_service),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="asc", regex="^(asc|desc)$"),
) -> list[MessageResponse]:
    """Get messages from a conversation."""
    try:
        messages = await chat_service.get_messages(
            user_id=current_user.id,
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
            order=order,
        )
        return messages
    except Exception as e:
        logger.error(f"Get messages error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/conversations/{conversation_id}/archive",
    response_model=ConversationResponse,
    summary="Archive conversation",
    description="Archive a conversation",
)
async def archive_conversation(
    conversation_id: UUID,
    current_user: CurrentUser,
    chat_service: ChatService = Depends(get_chat_service),
) -> ConversationResponse:
    """Archive a conversation."""
    try:
        conversation = await chat_service.update_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
            is_archived=True,
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Archive conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/conversations/{conversation_id}/unarchive",
    response_model=ConversationResponse,
    summary="Unarchive conversation",
    description="Restore an archived conversation",
)
async def unarchive_conversation(
    conversation_id: UUID,
    current_user: CurrentUser,
    chat_service: ChatService = Depends(get_chat_service),
) -> ConversationResponse:
    """Unarchive a conversation."""
    try:
        conversation = await chat_service.update_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
            is_archived=False,
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unarchive conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
