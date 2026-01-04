"""Chat and conversation schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.chat import MessageRole


class SendMessageRequest(BaseModel):
    """Request schema for sending a message."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=32000,
        description="Message content"
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Existing conversation ID (creates new if not provided)"
    )
    stream: bool = Field(
        default=True,
        description="Whether to stream the response"
    )
    include_memory: bool = Field(
        default=True,
        description="Whether to include memory context"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional message metadata"
    )


class MessageResponse(BaseModel):
    """Response schema for a message."""

    id: UUID = Field(..., description="Message ID")
    conversation_id: UUID = Field(..., description="Conversation ID")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    tokens: int | None = Field(default=None, description="Token count")
    created_at: datetime = Field(..., description="Creation timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class ConversationCreate(BaseModel):
    """Request schema for creating a conversation."""

    title: str | None = Field(
        default=None,
        max_length=200,
        description="Conversation title"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional conversation metadata"
    )
    initial_message: str | None = Field(
        default=None,
        description="Optional initial message to start the conversation"
    )


class ConversationUpdate(BaseModel):
    """Request schema for updating a conversation."""

    title: str | None = Field(
        default=None,
        max_length=200,
        description="New conversation title"
    )
    is_archived: bool | None = Field(
        default=None,
        description="Archive status"
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Updated metadata"
    )


class ConversationResponse(BaseModel):
    """Response schema for a conversation."""

    id: UUID = Field(..., description="Conversation ID")
    user_id: str = Field(..., description="Owner user ID")
    title: str | None = Field(default=None, description="Conversation title")
    summary: str | None = Field(default=None, description="Conversation summary")
    message_count: int = Field(default=0, description="Number of messages")
    total_tokens: int = Field(default=0, description="Total tokens used")
    is_active: bool = Field(default=True)
    is_archived: bool = Field(default=False)
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_message_at: datetime | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class ConversationDetailResponse(ConversationResponse):
    """Detailed conversation response including messages."""

    messages: list[MessageResponse] = Field(
        default_factory=list,
        description="Conversation messages"
    )


class ConversationListResponse(BaseModel):
    """Response schema for listing conversations."""

    conversations: list[ConversationResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total number of conversations")
    page: int = Field(default=1)
    page_size: int = Field(default=20)
    has_more: bool = Field(default=False)


class StreamChunk(BaseModel):
    """Schema for streaming response chunks."""

    type: str = Field(
        ...,
        description="Chunk type: text, metadata, error, done"
    )
    content: str | None = Field(
        default=None,
        description="Text content for text chunks"
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Metadata for metadata chunks"
    )
    error: str | None = Field(
        default=None,
        description="Error message for error chunks"
    )


class ChatCompletionRequest(BaseModel):
    """Request schema for chat completion (non-streaming)."""

    messages: list[dict[str, str]] = Field(
        ...,
        description="List of messages in OpenAI format"
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Existing conversation to continue"
    )
    include_memory: bool = Field(
        default=True,
        description="Whether to include memory context"
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=32000,
        description="Maximum tokens in response"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )


class ChatCompletionResponse(BaseModel):
    """Response schema for chat completion."""

    id: UUID = Field(..., description="Completion ID")
    conversation_id: UUID = Field(..., description="Conversation ID")
    message: MessageResponse = Field(..., description="Assistant message")
    usage: dict[str, int] = Field(
        default_factory=dict,
        description="Token usage statistics"
    )
    memory_context_used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
