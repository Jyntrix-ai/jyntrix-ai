"""FastAPI dependency injection functions."""

import logging
from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from qdrant_client import QdrantClient
from redis.asyncio import Redis
from supabase import Client as SupabaseClient

from src.config import settings
from src.db.qdrant import get_qdrant_client
from src.db.redis import get_redis_client
from src.db.supabase import get_supabase_client, get_supabase_admin_client
from src.models.user import User

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_supabase() -> SupabaseClient:
    """Get Supabase client dependency."""
    return get_supabase_client()


async def get_supabase_admin() -> SupabaseClient:
    """Get Supabase admin client with service role key."""
    return get_supabase_admin_client()


async def get_qdrant() -> QdrantClient:
    """Get Qdrant client dependency."""
    return get_qdrant_client()


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Get Redis client dependency with automatic cleanup."""
    client = await get_redis_client()
    try:
        yield client
    finally:
        # Connection pooling handles cleanup
        pass


async def verify_supabase_token(
    credentials: HTTPAuthorizationCredentials,
    supabase: SupabaseClient,
) -> dict:
    """Verify JWT token using Supabase."""
    try:
        token = credentials.credentials

        # Use Supabase to verify the token
        response = supabase.auth.get_user(token)

        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "id": response.user.id,
            "email": response.user.email,
            "user_metadata": response.user.user_metadata,
            "app_metadata": response.user.app_metadata,
        }

    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    supabase: Annotated[SupabaseClient, Depends(get_supabase)],
) -> User:
    """Get the current authenticated user from JWT token.

    This dependency extracts and validates the JWT token from the Authorization header,
    then returns the authenticated user.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_data = await verify_supabase_token(credentials, supabase)

    # Create User model from Supabase data
    user = User(
        id=user_data["id"],
        email=user_data.get("email", ""),
        full_name=user_data.get("user_metadata", {}).get("full_name"),
        avatar_url=user_data.get("user_metadata", {}).get("avatar_url"),
        metadata=user_data.get("user_metadata", {}),
    )

    return user


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    supabase: Annotated[SupabaseClient, Depends(get_supabase)],
) -> User | None:
    """Get the current user if authenticated, otherwise return None.

    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    if not credentials:
        return None

    try:
        user_data = await verify_supabase_token(credentials, supabase)
        return User(
            id=user_data["id"],
            email=user_data.get("email", ""),
            full_name=user_data.get("user_metadata", {}).get("full_name"),
            avatar_url=user_data.get("user_metadata", {}).get("avatar_url"),
            metadata=user_data.get("user_metadata", {}),
        )
    except HTTPException:
        return None


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
SupabaseDep = Annotated[SupabaseClient, Depends(get_supabase)]
SupabaseAdminDep = Annotated[SupabaseClient, Depends(get_supabase_admin)]
QdrantDep = Annotated[QdrantClient, Depends(get_qdrant)]
RedisDep = Annotated[Redis, Depends(get_redis)]
