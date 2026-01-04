"""Profile routes for user profile management."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.dependencies import CurrentUser, SupabaseDep
from src.models.user import MemorySettings, Profile

logger = logging.getLogger(__name__)

router = APIRouter()


class ProfileUpdate(BaseModel):
    """Request schema for profile updates."""

    display_name: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    timezone: str | None = Field(default=None, max_length=50)
    language: str | None = Field(default=None, max_length=10)
    preferences: dict[str, Any] | None = Field(default=None)


class MemorySettingsUpdate(BaseModel):
    """Request schema for memory settings updates."""

    memory_enabled: bool | None = None
    auto_extract: bool | None = None
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    max_memories_per_type: int | None = Field(default=None, ge=100, le=100000)
    semantic_extraction: bool | None = None
    entity_extraction: bool | None = None
    procedural_learning: bool | None = None


class ProfileResponse(BaseModel):
    """Response schema for profile."""

    id: UUID
    user_id: str
    display_name: str | None
    bio: str | None
    timezone: str
    language: str
    preferences: dict[str, Any]
    memory_settings: MemorySettings

    class Config:
        from_attributes = True


async def get_or_create_profile(supabase: SupabaseDep, user_id: str) -> dict:
    """Get existing profile or create a new one."""
    # Try to get existing profile
    response = supabase.table("profiles").select("*").eq("user_id", user_id).single().execute()

    if response.data:
        return response.data

    # Create new profile
    new_profile = {
        "user_id": user_id,
        "display_name": None,
        "bio": None,
        "timezone": "UTC",
        "language": "en",
        "preferences": {},
        "memory_settings": {
            "memory_enabled": True,
            "auto_extract": True,
            "retention_days": 365,
            "max_memories_per_type": 10000,
            "semantic_extraction": True,
            "entity_extraction": True,
            "procedural_learning": True,
        },
    }

    response = supabase.table("profiles").insert(new_profile).execute()
    return response.data[0] if response.data else new_profile


@router.get(
    "",
    response_model=ProfileResponse,
    summary="Get current user's profile",
    description="Get the profile for the currently authenticated user",
)
async def get_profile(
    current_user: CurrentUser,
    supabase: SupabaseDep,
) -> ProfileResponse:
    """Get the current user's profile."""
    try:
        profile_data = await get_or_create_profile(supabase, current_user.id)

        # Parse memory_settings if it's a dict
        memory_settings = profile_data.get("memory_settings", {})
        if isinstance(memory_settings, dict):
            memory_settings = MemorySettings(**memory_settings)

        return ProfileResponse(
            id=profile_data.get("id"),
            user_id=profile_data.get("user_id"),
            display_name=profile_data.get("display_name"),
            bio=profile_data.get("bio"),
            timezone=profile_data.get("timezone", "UTC"),
            language=profile_data.get("language", "en"),
            preferences=profile_data.get("preferences", {}),
            memory_settings=memory_settings,
        )
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.patch(
    "",
    response_model=ProfileResponse,
    summary="Update profile",
    description="Update the current user's profile",
)
async def update_profile(
    request: ProfileUpdate,
    current_user: CurrentUser,
    supabase: SupabaseDep,
) -> ProfileResponse:
    """Update the current user's profile."""
    try:
        # Build update dict with only provided fields
        update_data = {}
        if request.display_name is not None:
            update_data["display_name"] = request.display_name
        if request.bio is not None:
            update_data["bio"] = request.bio
        if request.timezone is not None:
            update_data["timezone"] = request.timezone
        if request.language is not None:
            update_data["language"] = request.language
        if request.preferences is not None:
            update_data["preferences"] = request.preferences

        if not update_data:
            # No updates, just return current profile
            profile_data = await get_or_create_profile(supabase, current_user.id)
        else:
            # Ensure profile exists first
            await get_or_create_profile(supabase, current_user.id)

            # Update profile
            response = (
                supabase.table("profiles")
                .update(update_data)
                .eq("user_id", current_user.id)
                .execute()
            )
            profile_data = response.data[0] if response.data else {}

        # Parse memory_settings
        memory_settings = profile_data.get("memory_settings", {})
        if isinstance(memory_settings, dict):
            memory_settings = MemorySettings(**memory_settings)

        return ProfileResponse(
            id=profile_data.get("id"),
            user_id=profile_data.get("user_id"),
            display_name=profile_data.get("display_name"),
            bio=profile_data.get("bio"),
            timezone=profile_data.get("timezone", "UTC"),
            language=profile_data.get("language", "en"),
            preferences=profile_data.get("preferences", {}),
            memory_settings=memory_settings,
        )
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/memory-settings",
    response_model=MemorySettings,
    summary="Get memory settings",
    description="Get the memory settings for the current user",
)
async def get_memory_settings(
    current_user: CurrentUser,
    supabase: SupabaseDep,
) -> MemorySettings:
    """Get memory settings for the current user."""
    try:
        profile_data = await get_or_create_profile(supabase, current_user.id)
        memory_settings = profile_data.get("memory_settings", {})

        if isinstance(memory_settings, dict):
            return MemorySettings(**memory_settings)
        return memory_settings
    except Exception as e:
        logger.error(f"Get memory settings error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.patch(
    "/memory-settings",
    response_model=MemorySettings,
    summary="Update memory settings",
    description="Update the memory settings for the current user",
)
async def update_memory_settings(
    request: MemorySettingsUpdate,
    current_user: CurrentUser,
    supabase: SupabaseDep,
) -> MemorySettings:
    """Update memory settings for the current user."""
    try:
        # Get current profile
        profile_data = await get_or_create_profile(supabase, current_user.id)
        current_settings = profile_data.get("memory_settings", {})

        # Merge with updates
        update_dict = request.model_dump(exclude_unset=True)
        new_settings = {**current_settings, **update_dict}

        # Update in database
        response = (
            supabase.table("profiles")
            .update({"memory_settings": new_settings})
            .eq("user_id", current_user.id)
            .execute()
        )

        return MemorySettings(**new_settings)
    except Exception as e:
        logger.error(f"Update memory settings error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/memory-settings/reset",
    response_model=MemorySettings,
    summary="Reset memory settings",
    description="Reset memory settings to defaults",
)
async def reset_memory_settings(
    current_user: CurrentUser,
    supabase: SupabaseDep,
) -> MemorySettings:
    """Reset memory settings to defaults."""
    try:
        default_settings = MemorySettings()

        # Update in database
        response = (
            supabase.table("profiles")
            .update({"memory_settings": default_settings.model_dump()})
            .eq("user_id", current_user.id)
            .execute()
        )

        return default_settings
    except Exception as e:
        logger.error(f"Reset memory settings error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete profile",
    description="Delete the current user's profile data (not the account)",
)
async def delete_profile(
    current_user: CurrentUser,
    supabase: SupabaseDep,
) -> None:
    """Delete the current user's profile data."""
    try:
        supabase.table("profiles").delete().eq("user_id", current_user.id).execute()
    except Exception as e:
        logger.error(f"Delete profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
