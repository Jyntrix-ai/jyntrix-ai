"""User and Profile models."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    """User model representing an authenticated user."""

    id: str = Field(..., description="Unique user identifier from Supabase")
    email: str = Field(..., description="User's email address")
    full_name: str | None = Field(default=None, description="User's full name")
    avatar_url: str | None = Field(default=None, description="URL to user's avatar")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional user metadata")

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class MemorySettings(BaseModel):
    """User's memory-related settings."""

    memory_enabled: bool = Field(default=True, description="Whether memory is enabled")
    auto_extract: bool = Field(
        default=True,
        description="Automatically extract and store memories"
    )
    retention_days: int = Field(
        default=365,
        description="How long to retain episodic memories"
    )
    max_memories_per_type: int = Field(
        default=10000,
        description="Maximum memories per type"
    )
    semantic_extraction: bool = Field(
        default=True,
        description="Extract semantic memories from conversations"
    )
    entity_extraction: bool = Field(
        default=True,
        description="Extract entities from conversations"
    )
    procedural_learning: bool = Field(
        default=True,
        description="Learn procedural patterns"
    )


class Profile(BaseModel):
    """User profile with extended information stored in Supabase."""

    id: UUID = Field(..., description="Profile UUID")
    user_id: str = Field(..., description="Reference to auth user")
    display_name: str | None = Field(default=None, description="Display name")
    bio: str | None = Field(default=None, description="User bio")
    timezone: str = Field(default="UTC", description="User's timezone")
    language: str = Field(default="en", description="Preferred language")
    preferences: dict[str, Any] = Field(
        default_factory=dict,
        description="User preferences (theme, notifications, etc.)"
    )
    memory_settings: MemorySettings = Field(
        default_factory=lambda: MemorySettings(),
        description="Memory-related settings"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class UserStats(BaseModel):
    """Statistics about a user's memory usage."""

    user_id: str
    total_conversations: int = 0
    total_messages: int = 0
    profile_memories: int = 0
    semantic_memories: int = 0
    episodic_memories: int = 0
    procedural_memories: int = 0
    total_entities: int = 0
    storage_used_bytes: int = 0
    last_activity: datetime | None = None

    class Config:
        """Pydantic configuration."""

        from_attributes = True
