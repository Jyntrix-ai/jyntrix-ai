"""Chat and conversation models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of the message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """Individual message in a conversation."""

    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID = Field(..., description="Parent conversation ID")
    role: MessageRole = Field(..., description="Who sent the message")
    content: str = Field(..., description="Message content")
    tokens: int | None = Field(default=None, description="Token count")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Memory extraction metadata
    memories_extracted: bool = Field(
        default=False,
        description="Whether memories were extracted from this message"
    )
    extracted_memory_ids: list[UUID] = Field(
        default_factory=list,
        description="IDs of memories extracted from this message"
    )

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class Conversation(BaseModel):
    """Conversation containing multiple messages."""

    id: UUID = Field(default_factory=uuid4)
    user_id: str = Field(..., description="Owner user ID")
    title: str | None = Field(default=None, description="Conversation title")
    summary: str | None = Field(
        default=None,
        description="AI-generated summary of the conversation"
    )
    messages: list[Message] = Field(default_factory=list)
    message_count: int = Field(default=0)
    total_tokens: int = Field(default=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Status flags
    is_active: bool = Field(default=True)
    is_archived: bool = Field(default=False)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: datetime | None = Field(default=None)

    # Memory extraction status
    memories_processed: bool = Field(
        default=False,
        description="Whether memories have been extracted"
    )
    processing_status: str = Field(
        default="pending",
        description="pending, processing, completed, failed"
    )

    class Config:
        """Pydantic configuration."""

        from_attributes = True

    def add_message(self, role: MessageRole, content: str, tokens: int | None = None) -> Message:
        """Add a new message to the conversation."""
        message = Message(
            conversation_id=self.id,
            role=role,
            content=content,
            tokens=tokens,
        )
        self.messages.append(message)
        self.message_count += 1
        if tokens:
            self.total_tokens += tokens
        self.last_message_at = message.created_at
        self.updated_at = datetime.utcnow()
        return message


class ConversationSummary(BaseModel):
    """Lightweight conversation summary for listing."""

    id: UUID
    user_id: str
    title: str | None
    summary: str | None
    message_count: int
    last_message_at: datetime | None
    created_at: datetime
    is_archived: bool = False

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class StreamEvent(BaseModel):
    """Server-Sent Event for streaming responses."""

    event: str = Field(..., description="Event type: message, error, done")
    data: str = Field(..., description="Event data (JSON string)")
    id: str | None = Field(default=None, description="Event ID")
    retry: int | None = Field(default=None, description="Retry interval in ms")


class ChatContext(BaseModel):
    """Context assembled for chat completion."""

    conversation_id: UUID
    user_id: str
    messages: list[Message]
    memory_context: str | None = Field(default=None)
    system_prompt: str | None = Field(default=None)
    total_context_tokens: int = Field(default=0)


class QueryAnalysis(BaseModel):
    """Analysis of user query for retrieval."""

    original_query: str
    intent: str = Field(
        ...,
        description="Query intent: question, command, conversation, recall"
    )
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    entities_mentioned: list[str] = Field(default_factory=list)
    time_reference: str | None = Field(
        default=None,
        description="Time reference in query if any"
    )
    requires_memory: bool = Field(
        default=True,
        description="Whether this query needs memory retrieval"
    )
    memory_types_needed: list[str] = Field(
        default_factory=list,
        description="Which memory types to search"
    )
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
