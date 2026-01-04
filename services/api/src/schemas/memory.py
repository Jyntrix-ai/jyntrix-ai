"""Memory schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.memory import MemoryType


class MemoryCreate(BaseModel):
    """Request schema for creating a memory."""

    memory_type: MemoryType = Field(..., description="Type of memory")
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Memory content"
    )
    keywords: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Keywords for search"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    reliability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Reliability score"
    )

    # Profile memory specific fields
    category: str | None = Field(
        default=None,
        description="Category for profile memories"
    )
    attribute: str | None = Field(
        default=None,
        description="Attribute name for profile memories"
    )
    value: str | None = Field(
        default=None,
        description="Attribute value for profile memories"
    )

    # Semantic memory specific fields
    topic: str | None = Field(
        default=None,
        description="Topic for semantic memories"
    )
    fact: str | None = Field(
        default=None,
        description="Factual content for semantic memories"
    )

    # Episodic memory specific fields
    conversation_id: UUID | None = Field(
        default=None,
        description="Source conversation for episodic memories"
    )
    event_type: str | None = Field(
        default=None,
        description="Event type for episodic memories"
    )
    summary: str | None = Field(
        default=None,
        description="Summary for episodic memories"
    )

    # Procedural memory specific fields
    procedure_name: str | None = Field(
        default=None,
        description="Procedure name for procedural memories"
    )
    trigger: str | None = Field(
        default=None,
        description="Trigger for procedural memories"
    )
    steps: list[str] | None = Field(
        default=None,
        description="Steps for procedural memories"
    )


class MemoryUpdate(BaseModel):
    """Request schema for updating a memory."""

    content: str | None = Field(
        default=None,
        max_length=10000,
        description="Updated content"
    )
    keywords: list[str] | None = Field(
        default=None,
        max_length=20,
        description="Updated keywords"
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Updated metadata"
    )
    reliability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Updated reliability score"
    )

    # Type-specific updates
    category: str | None = None
    attribute: str | None = None
    value: str | None = None
    topic: str | None = None
    fact: str | None = None
    summary: str | None = None
    procedure_name: str | None = None
    trigger: str | None = None
    steps: list[str] | None = None


class MemoryResponse(BaseModel):
    """Response schema for a memory."""

    id: UUID = Field(..., description="Memory ID")
    user_id: str = Field(..., description="Owner user ID")
    memory_type: MemoryType = Field(..., description="Type of memory")
    content: str = Field(..., description="Memory content")
    keywords: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    reliability: float = Field(default=0.5)
    access_count: int = Field(default=0)
    last_accessed: datetime | None = Field(default=None)
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Type-specific fields (included based on memory_type)
    category: str | None = None
    attribute: str | None = None
    value: str | None = None
    topic: str | None = None
    subtopic: str | None = None
    fact: str | None = None
    conversation_id: UUID | None = None
    event_type: str | None = None
    summary: str | None = None
    procedure_name: str | None = None
    trigger: str | None = None
    steps: list[str] | None = None

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class MemorySearchRequest(BaseModel):
    """Request schema for searching memories."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query"
    )
    memory_types: list[MemoryType] | None = Field(
        default=None,
        description="Filter by memory types"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum results to return"
    )
    min_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score"
    )
    include_vector_search: bool = Field(
        default=True,
        description="Include vector similarity search"
    )
    include_keyword_search: bool = Field(
        default=True,
        description="Include keyword search"
    )
    date_from: datetime | None = Field(
        default=None,
        description="Filter memories created after this date"
    )
    date_to: datetime | None = Field(
        default=None,
        description="Filter memories created before this date"
    )


class MemorySearchResultItem(BaseModel):
    """Single item in memory search results."""

    memory: MemoryResponse = Field(..., description="The memory")
    score: float = Field(..., description="Combined relevance score")
    keyword_score: float = Field(default=0.0)
    vector_score: float = Field(default=0.0)
    reliability_score: float = Field(default=0.0)
    recency_score: float = Field(default=0.0)
    frequency_score: float = Field(default=0.0)
    match_type: str = Field(
        default="hybrid",
        description="Type of match"
    )


class MemorySearchResponse(BaseModel):
    """Response schema for memory search."""

    results: list[MemorySearchResultItem] = Field(default_factory=list)
    total: int = Field(..., description="Total matching memories")
    query: str = Field(..., description="Original query")
    search_time_ms: float = Field(..., description="Search time in milliseconds")


class MemoryListResponse(BaseModel):
    """Response schema for listing memories."""

    memories: list[MemoryResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total memories")
    page: int = Field(default=1)
    page_size: int = Field(default=20)
    has_more: bool = Field(default=False)


class MemoryStatsResponse(BaseModel):
    """Response schema for memory statistics."""

    user_id: str = Field(..., description="User ID")
    total_memories: int = Field(default=0)
    profile_memories: int = Field(default=0)
    semantic_memories: int = Field(default=0)
    episodic_memories: int = Field(default=0)
    procedural_memories: int = Field(default=0)
    total_entities: int = Field(default=0)
    total_relations: int = Field(default=0)
    average_reliability: float = Field(default=0.0)
    oldest_memory: datetime | None = Field(default=None)
    newest_memory: datetime | None = Field(default=None)


class BulkMemoryCreate(BaseModel):
    """Request schema for bulk memory creation."""

    memories: list[MemoryCreate] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of memories to create"
    )


class BulkMemoryResponse(BaseModel):
    """Response schema for bulk memory operations."""

    created: int = Field(default=0, description="Number created")
    failed: int = Field(default=0, description="Number failed")
    errors: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Error details for failed items"
    )
    memory_ids: list[UUID] = Field(
        default_factory=list,
        description="IDs of created memories"
    )
