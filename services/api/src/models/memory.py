"""Memory models for the AI Memory Architecture."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Types of memories in the system."""

    PROFILE = "profile"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


class ReliabilityLevel(str, Enum):
    """Reliability levels for memories."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class Memory(BaseModel):
    """Base memory model with common fields."""

    id: UUID = Field(default_factory=uuid4)
    user_id: str = Field(..., description="Owner user ID")
    memory_type: MemoryType = Field(..., description="Type of memory")
    content: str = Field(..., description="Memory content")
    keywords: list[str] = Field(default_factory=list, description="Extracted keywords")
    embedding: list[float] | None = Field(
        default=None,
        description="Vector embedding (384 dimensions)"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    reliability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Reliability score"
    )
    access_count: int = Field(default=0, description="Number of times accessed")
    last_accessed: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class ProfileMemory(Memory):
    """Profile memory for persistent user information."""

    memory_type: MemoryType = Field(default=MemoryType.PROFILE)
    category: str = Field(
        ...,
        description="Category: personal_info, preferences, goals, background"
    )
    attribute: str = Field(..., description="Specific attribute name")
    value: str = Field(..., description="Attribute value")
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence in this information"
    )
    source: str = Field(
        default="user_stated",
        description="Source: user_stated, inferred, verified"
    )
    is_verified: bool = Field(default=False)

    @property
    def content(self) -> str:
        """Generate content from attribute and value."""
        return f"{self.attribute}: {self.value}"


class SemanticMemory(Memory):
    """Semantic memory for factual knowledge and beliefs."""

    memory_type: MemoryType = Field(default=MemoryType.SEMANTIC)
    topic: str = Field(..., description="Main topic of the memory")
    subtopic: str | None = Field(default=None, description="Subtopic if applicable")
    fact: str = Field(..., description="The factual content")
    context: str | None = Field(
        default=None,
        description="Context in which this was learned"
    )
    related_entities: list[str] = Field(
        default_factory=list,
        description="Related entity IDs"
    )
    contradicts: list[UUID] | None = Field(
        default=None,
        description="IDs of potentially contradicting memories"
    )
    source_conversation_id: UUID | None = Field(
        default=None,
        description="Conversation where this was extracted"
    )


class EpisodicMemory(Memory):
    """Episodic memory for specific events and interactions."""

    memory_type: MemoryType = Field(default=MemoryType.EPISODIC)
    conversation_id: UUID = Field(..., description="Source conversation ID")
    event_type: str = Field(
        ...,
        description="Type: conversation, request, decision, achievement"
    )
    summary: str = Field(..., description="Summary of the event")
    participants: list[str] = Field(
        default_factory=list,
        description="Participants in the event"
    )
    location: str | None = Field(default=None, description="Location context if any")
    emotional_context: str | None = Field(
        default=None,
        description="Emotional context of the event"
    )
    outcome: str | None = Field(default=None, description="Outcome of the event")
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Importance score"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the event occurred"
    )


class ProceduralMemory(Memory):
    """Procedural memory for learned patterns and procedures."""

    memory_type: MemoryType = Field(default=MemoryType.PROCEDURAL)
    procedure_name: str = Field(..., description="Name of the procedure")
    trigger: str = Field(..., description="What triggers this procedure")
    steps: list[str] = Field(..., description="Steps in the procedure")
    conditions: list[str] | None = Field(
        default=None,
        description="Conditions for this procedure"
    )
    success_rate: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Historical success rate"
    )
    execution_count: int = Field(
        default=0,
        description="Number of times executed"
    )
    last_executed: datetime | None = Field(default=None)
    learned_from: list[UUID] | None = Field(
        default=None,
        description="Conversation IDs where this was learned"
    )


class MemorySearchResult(BaseModel):
    """Result from memory search with scoring."""

    memory: Memory
    score: float = Field(..., description="Combined relevance score")
    keyword_score: float = Field(default=0.0)
    vector_score: float = Field(default=0.0)
    reliability_score: float = Field(default=0.0)
    recency_score: float = Field(default=0.0)
    frequency_score: float = Field(default=0.0)
    match_type: str = Field(
        default="hybrid",
        description="Type of match: keyword, vector, hybrid"
    )


class MemoryContext(BaseModel):
    """Assembled memory context for LLM."""

    profile_memories: list[ProfileMemory] = Field(default_factory=list)
    semantic_memories: list[SemanticMemory] = Field(default_factory=list)
    episodic_memories: list[EpisodicMemory] = Field(default_factory=list)
    procedural_memories: list[ProceduralMemory] = Field(default_factory=list)
    entity_context: str | None = Field(default=None)
    total_tokens: int = Field(default=0)
    truncated: bool = Field(default=False)

    def to_prompt_context(self) -> str:
        """Convert memory context to prompt format."""
        sections = []

        if self.profile_memories:
            profile_text = "## User Profile\n"
            for mem in self.profile_memories:
                profile_text += f"- {mem.category}/{mem.attribute}: {mem.value}\n"
            sections.append(profile_text)

        if self.semantic_memories:
            semantic_text = "## Known Facts\n"
            for mem in self.semantic_memories:
                semantic_text += f"- [{mem.topic}] {mem.fact}\n"
            sections.append(semantic_text)

        if self.episodic_memories:
            episodic_text = "## Recent Interactions\n"
            for mem in self.episodic_memories:
                episodic_text += f"- {mem.timestamp.strftime('%Y-%m-%d')}: {mem.summary}\n"
            sections.append(episodic_text)

        if self.procedural_memories:
            procedural_text = "## Learned Procedures\n"
            for mem in self.procedural_memories:
                procedural_text += f"- {mem.procedure_name}: {mem.trigger}\n"
            sections.append(procedural_text)

        if self.entity_context:
            sections.append(f"## Entity Context\n{self.entity_context}")

        return "\n\n".join(sections)
