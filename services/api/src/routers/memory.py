"""Memory CRUD routes."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from src.dependencies import CurrentUser, QdrantDep, RedisDep, SupabaseAdminDep
from src.models.memory import MemoryType
from src.schemas.memory import (
    BulkMemoryCreate,
    BulkMemoryResponse,
    MemoryCreate,
    MemoryListResponse,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryStatsResponse,
    MemoryUpdate,
)
from src.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_memory_service(
    supabase: SupabaseAdminDep,
    qdrant: QdrantDep,
    redis: RedisDep,
) -> MemoryService:
    """Get memory service instance."""
    return MemoryService(supabase=supabase, qdrant=qdrant, redis=redis)


@router.post(
    "",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new memory",
    description="Create a new memory of any type",
)
async def create_memory(
    request: MemoryCreate,
    current_user: CurrentUser,
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Create a new memory."""
    try:
        memory = await memory_service.create_memory(
            user_id=current_user.id,
            memory_data=request,
        )
        return memory
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Create memory error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/bulk",
    response_model=BulkMemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create multiple memories",
    description="Create multiple memories in a single request",
)
async def create_memories_bulk(
    request: BulkMemoryCreate,
    current_user: CurrentUser,
    memory_service: MemoryService = Depends(get_memory_service),
) -> BulkMemoryResponse:
    """Create multiple memories."""
    try:
        result = await memory_service.create_memories_bulk(
            user_id=current_user.id,
            memories=request.memories,
        )
        return result
    except Exception as e:
        logger.error(f"Bulk create memories error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "",
    response_model=MemoryListResponse,
    summary="List memories",
    description="Get paginated list of user's memories",
)
async def list_memories(
    current_user: CurrentUser,
    memory_service: MemoryService = Depends(get_memory_service),
    memory_type: MemoryType | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> MemoryListResponse:
    """List user's memories."""
    try:
        result = await memory_service.list_memories(
            user_id=current_user.id,
            memory_type=memory_type,
            page=page,
            page_size=page_size,
        )
        return result
    except Exception as e:
        logger.error(f"List memories error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/search",
    response_model=MemorySearchResponse,
    summary="Search memories",
    description="Search memories using hybrid search (keyword + vector)",
)
async def search_memories(
    request: MemorySearchRequest,
    current_user: CurrentUser,
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemorySearchResponse:
    """Search user's memories."""
    try:
        result = await memory_service.search_memories(
            user_id=current_user.id,
            query=request.query,
            memory_types=request.memory_types,
            limit=request.limit,
            min_score=request.min_score,
            include_vector_search=request.include_vector_search,
            include_keyword_search=request.include_keyword_search,
            date_from=request.date_from,
            date_to=request.date_to,
        )
        return result
    except Exception as e:
        logger.error(f"Search memories error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/stats",
    response_model=MemoryStatsResponse,
    summary="Get memory statistics",
    description="Get statistics about user's memories",
)
async def get_memory_stats(
    current_user: CurrentUser,
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryStatsResponse:
    """Get memory statistics for the user."""
    try:
        stats = await memory_service.get_stats(user_id=current_user.id)
        return stats
    except Exception as e:
        logger.error(f"Get memory stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Get memory by ID",
    description="Get a specific memory by its ID",
)
async def get_memory(
    memory_id: UUID,
    current_user: CurrentUser,
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Get a specific memory."""
    try:
        memory = await memory_service.get_memory(
            user_id=current_user.id,
            memory_id=memory_id,
        )
        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found",
            )
        return memory
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get memory error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.patch(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Update memory",
    description="Update an existing memory",
)
async def update_memory(
    memory_id: UUID,
    request: MemoryUpdate,
    current_user: CurrentUser,
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Update a memory."""
    try:
        memory = await memory_service.update_memory(
            user_id=current_user.id,
            memory_id=memory_id,
            update_data=request,
        )
        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found",
            )
        return memory
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update memory error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete memory",
    description="Permanently delete a memory",
)
async def delete_memory(
    memory_id: UUID,
    current_user: CurrentUser,
    memory_service: MemoryService = Depends(get_memory_service),
) -> Response:
    """Delete a memory."""
    try:
        deleted = await memory_service.delete_memory(
            user_id=current_user.id,
            memory_id=memory_id,
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found",
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete memory error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete all memories",
    description="Delete all memories for the current user",
)
async def delete_all_memories(
    current_user: CurrentUser,
    memory_service: MemoryService = Depends(get_memory_service),
    memory_type: MemoryType | None = Query(default=None),
    confirm: bool = Query(default=False),
) -> Response:
    """Delete all user's memories (optionally filtered by type)."""
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required. Set confirm=true to delete all memories.",
        )

    try:
        await memory_service.delete_all_memories(
            user_id=current_user.id,
            memory_type=memory_type,
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        logger.error(f"Delete all memories error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/{memory_id}/access",
    response_model=MemoryResponse,
    summary="Record memory access",
    description="Record that a memory was accessed (updates access count and timestamp)",
)
async def record_memory_access(
    memory_id: UUID,
    current_user: CurrentUser,
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Record memory access for ranking purposes."""
    try:
        memory = await memory_service.record_access(
            user_id=current_user.id,
            memory_id=memory_id,
        )
        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found",
            )
        return memory
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Record memory access error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/type/{memory_type}",
    response_model=MemoryListResponse,
    summary="Get memories by type",
    description="Get memories of a specific type",
)
async def get_memories_by_type(
    memory_type: MemoryType,
    current_user: CurrentUser,
    memory_service: MemoryService = Depends(get_memory_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> MemoryListResponse:
    """Get memories filtered by type."""
    try:
        result = await memory_service.list_memories(
            user_id=current_user.id,
            memory_type=memory_type,
            page=page,
            page_size=page_size,
        )
        return result
    except Exception as e:
        logger.error(f"Get memories by type error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
