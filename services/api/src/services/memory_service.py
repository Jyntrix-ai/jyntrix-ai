"""Memory service for CRUD operations with user isolation."""

import logging
import time
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from redis.asyncio import Redis
from supabase import Client as SupabaseClient

from src.config import settings
from src.core.embeddings import get_embedding_service
from src.core.hybrid_ranker import HybridRanker
from src.core.keyword_search import KeywordSearch
from src.core.vector_search import VectorSearch
from src.models.memory import MemoryType
from src.schemas.memory import (
    BulkMemoryResponse,
    MemoryCreate,
    MemoryListResponse,
    MemoryResponse,
    MemorySearchResponse,
    MemorySearchResultItem,
    MemoryStatsResponse,
    MemoryUpdate,
)

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for memory CRUD operations with strict user isolation."""

    def __init__(
        self,
        supabase: SupabaseClient,
        qdrant: QdrantClient,
        redis: Redis,
    ):
        """Initialize memory service."""
        self.supabase = supabase
        self.qdrant = qdrant
        self.redis = redis
        self.embedder = get_embedding_service()
        self.vector_search = VectorSearch(qdrant)
        self.keyword_search = KeywordSearch()
        self.hybrid_ranker = HybridRanker()

    async def create_memory(
        self,
        user_id: str,
        memory_data: MemoryCreate,
    ) -> MemoryResponse:
        """Create a new memory with embedding.

        Args:
            user_id: Owner user ID
            memory_data: Memory creation data

        Returns:
            Created memory response
        """
        memory_id = uuid4()
        now = datetime.utcnow()

        # Generate embedding for the content
        embedding = self.embedder.embed(memory_data.content)

        # Extract keywords if not provided
        keywords = memory_data.keywords
        if not keywords:
            keywords = self._extract_keywords(memory_data.content)

        # Build memory record for Supabase
        memory_record = {
            "id": str(memory_id),
            "user_id": user_id,
            "memory_type": memory_data.memory_type.value,
            "content": memory_data.content,
            "keywords": keywords,
            "metadata": memory_data.metadata,
            "reliability": memory_data.reliability,
            "access_count": 0,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        # Add type-specific fields
        if memory_data.memory_type == MemoryType.PROFILE:
            memory_record.update({
                "category": memory_data.category,
                "attribute": memory_data.attribute,
                "value": memory_data.value,
            })
        elif memory_data.memory_type == MemoryType.SEMANTIC:
            memory_record.update({
                "topic": memory_data.topic,
                "fact": memory_data.fact,
            })
        elif memory_data.memory_type == MemoryType.EPISODIC:
            memory_record.update({
                "conversation_id": str(memory_data.conversation_id) if memory_data.conversation_id else None,
                "event_type": memory_data.event_type,
                "summary": memory_data.summary,
            })
        elif memory_data.memory_type == MemoryType.PROCEDURAL:
            memory_record.update({
                "procedure_name": memory_data.procedure_name,
                "trigger": memory_data.trigger,
                "steps": memory_data.steps,
            })

        # Save to Supabase
        response = self.supabase.table("memories").insert(memory_record).execute()

        # Save to Qdrant with user_id for filtering
        point = PointStruct(
            id=str(memory_id),
            vector=embedding,
            payload={
                "user_id": user_id,
                "memory_type": memory_data.memory_type.value,
                "content": memory_data.content,
                "keywords": keywords,
                "reliability": memory_data.reliability,
                "created_at": now.isoformat(),
            },
        )

        self.qdrant.upsert(
            collection_name=settings.qdrant_collection_name,
            points=[point],
        )

        # Invalidate cache
        await self._invalidate_cache(user_id)

        return self._to_response(response.data[0] if response.data else memory_record)

    async def create_memories_bulk(
        self,
        user_id: str,
        memories: list[MemoryCreate],
    ) -> BulkMemoryResponse:
        """Create multiple memories in bulk.

        Args:
            user_id: Owner user ID
            memories: List of memories to create

        Returns:
            Bulk creation response
        """
        created = 0
        failed = 0
        errors = []
        memory_ids = []

        for i, memory_data in enumerate(memories):
            try:
                response = await self.create_memory(user_id, memory_data)
                memory_ids.append(response.id)
                created += 1
            except Exception as e:
                failed += 1
                errors.append({
                    "index": i,
                    "error": str(e),
                })

        return BulkMemoryResponse(
            created=created,
            failed=failed,
            errors=errors,
            memory_ids=memory_ids,
        )

    async def get_memory(
        self,
        user_id: str,
        memory_id: UUID,
    ) -> MemoryResponse | None:
        """Get a specific memory by ID with user isolation.

        Args:
            user_id: Owner user ID
            memory_id: Memory ID

        Returns:
            Memory response or None if not found
        """
        try:
            response = (
                self.supabase.table("memories")
                .select("*")
                .eq("id", str(memory_id))
                .eq("user_id", user_id)
                .single()
                .execute()
            )

            if not response.data:
                return None

            return self._to_response(response.data)

        except Exception as e:
            logger.error(f"Get memory error: {e}")
            return None

    async def list_memories(
        self,
        user_id: str,
        memory_type: MemoryType | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> MemoryListResponse:
        """List user's memories with pagination.

        Args:
            user_id: Owner user ID
            memory_type: Optional filter by type
            page: Page number
            page_size: Items per page

        Returns:
            Paginated memory list
        """
        offset = (page - 1) * page_size

        query = (
            self.supabase.table("memories")
            .select("*", count="exact")
            .eq("user_id", user_id)
        )

        if memory_type:
            query = query.eq("memory_type", memory_type.value)

        response = (
            query
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

        memories = [self._to_response(m) for m in response.data or []]
        total = response.count or len(memories)

        return MemoryListResponse(
            memories=memories,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )

    async def update_memory(
        self,
        user_id: str,
        memory_id: UUID,
        update_data: MemoryUpdate,
    ) -> MemoryResponse | None:
        """Update an existing memory.

        Args:
            user_id: Owner user ID
            memory_id: Memory ID
            update_data: Fields to update

        Returns:
            Updated memory or None if not found
        """
        # Verify ownership
        existing = await self.get_memory(user_id, memory_id)
        if not existing:
            return None

        # Build update dict
        update_dict = {"updated_at": datetime.utcnow().isoformat()}

        if update_data.content is not None:
            update_dict["content"] = update_data.content
            # Regenerate embedding
            embedding = self.embedder.embed(update_data.content)
            # Update Qdrant
            self.qdrant.upsert(
                collection_name=settings.qdrant_collection_name,
                points=[
                    PointStruct(
                        id=str(memory_id),
                        vector=embedding,
                        payload={
                            "user_id": user_id,
                            "memory_type": existing.memory_type.value,
                            "content": update_data.content,
                            "keywords": update_data.keywords or existing.keywords,
                            "reliability": update_data.reliability or existing.reliability,
                            "created_at": existing.created_at.isoformat(),
                        },
                    )
                ],
            )

        if update_data.keywords is not None:
            update_dict["keywords"] = update_data.keywords
        if update_data.metadata is not None:
            update_dict["metadata"] = update_data.metadata
        if update_data.reliability is not None:
            update_dict["reliability"] = update_data.reliability

        # Type-specific updates
        for field in ["category", "attribute", "value", "topic", "fact",
                      "summary", "procedure_name", "trigger", "steps"]:
            value = getattr(update_data, field, None)
            if value is not None:
                update_dict[field] = value

        # Update in Supabase
        response = (
            self.supabase.table("memories")
            .update(update_dict)
            .eq("id", str(memory_id))
            .eq("user_id", user_id)
            .execute()
        )

        # Invalidate cache
        await self._invalidate_cache(user_id)

        return self._to_response(response.data[0]) if response.data else None

    async def delete_memory(
        self,
        user_id: str,
        memory_id: UUID,
    ) -> bool:
        """Delete a memory.

        Args:
            user_id: Owner user ID
            memory_id: Memory ID

        Returns:
            True if deleted, False if not found
        """
        # Verify ownership
        existing = await self.get_memory(user_id, memory_id)
        if not existing:
            return False

        # Delete from Supabase
        self.supabase.table("memories").delete().eq(
            "id", str(memory_id)
        ).eq("user_id", user_id).execute()

        # Delete from Qdrant
        self.qdrant.delete(
            collection_name=settings.qdrant_collection_name,
            points_selector=[str(memory_id)],
        )

        # Invalidate cache
        await self._invalidate_cache(user_id)

        return True

    async def delete_all_memories(
        self,
        user_id: str,
        memory_type: MemoryType | None = None,
    ) -> None:
        """Delete all memories for a user.

        Args:
            user_id: Owner user ID
            memory_type: Optional type filter
        """
        # Build query
        query = self.supabase.table("memories").delete().eq("user_id", user_id)
        if memory_type:
            query = query.eq("memory_type", memory_type.value)

        # Get IDs first for Qdrant deletion
        select_query = self.supabase.table("memories").select("id").eq("user_id", user_id)
        if memory_type:
            select_query = select_query.eq("memory_type", memory_type.value)
        ids_response = select_query.execute()

        memory_ids = [m["id"] for m in ids_response.data or []]

        # Delete from Supabase
        query.execute()

        # Delete from Qdrant
        if memory_ids:
            self.qdrant.delete(
                collection_name=settings.qdrant_collection_name,
                points_selector=memory_ids,
            )

        # Invalidate cache
        await self._invalidate_cache(user_id)

    async def search_memories(
        self,
        user_id: str,
        query: str,
        memory_types: list[MemoryType] | None = None,
        limit: int = 10,
        min_score: float = 0.0,
        include_vector_search: bool = True,
        include_keyword_search: bool = True,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> MemorySearchResponse:
        """Search memories using hybrid search.

        Args:
            user_id: Owner user ID
            query: Search query
            memory_types: Optional type filters
            limit: Maximum results
            min_score: Minimum relevance score
            include_vector_search: Use vector similarity
            include_keyword_search: Use keyword matching
            date_from: Start date filter
            date_to: End date filter

        Returns:
            Search results with scores
        """
        start_time = time.time()
        results = []

        # Vector search
        if include_vector_search:
            vector_results = await self.vector_search.search(
                user_id=user_id,
                query=query,
                memory_types=[t.value for t in memory_types] if memory_types else None,
                limit=limit * 2,  # Get more for merging
            )
            results.extend(vector_results)

        # Keyword search
        if include_keyword_search:
            keyword_results = await self._keyword_search(
                user_id=user_id,
                query=query,
                memory_types=memory_types,
                limit=limit * 2,
            )
            results.extend(keyword_results)

        # Deduplicate and rank
        ranked_results = self.hybrid_ranker.rank(results)

        # Apply score filter and limit
        filtered_results = [
            r for r in ranked_results
            if r.get("score", 0) >= min_score
        ][:limit]

        # Convert to response format
        search_results = []
        for r in filtered_results:
            memory = await self.get_memory(user_id, UUID(r["memory_id"]))
            if memory:
                search_results.append(MemorySearchResultItem(
                    memory=memory,
                    score=r.get("score", 0),
                    keyword_score=r.get("keyword_score", 0),
                    vector_score=r.get("vector_score", 0),
                    reliability_score=r.get("reliability_score", 0),
                    recency_score=r.get("recency_score", 0),
                    frequency_score=r.get("frequency_score", 0),
                    match_type=r.get("match_type", "hybrid"),
                ))

        elapsed = (time.time() - start_time) * 1000

        return MemorySearchResponse(
            results=search_results,
            total=len(search_results),
            query=query,
            search_time_ms=elapsed,
        )

    async def record_access(
        self,
        user_id: str,
        memory_id: UUID,
    ) -> MemoryResponse | None:
        """Record memory access for ranking purposes.

        Args:
            user_id: Owner user ID
            memory_id: Memory ID

        Returns:
            Updated memory or None
        """
        # Verify ownership
        existing = await self.get_memory(user_id, memory_id)
        if not existing:
            return None

        # Update access count and timestamp
        response = (
            self.supabase.table("memories")
            .update({
                "access_count": existing.access_count + 1,
                "last_accessed": datetime.utcnow().isoformat(),
            })
            .eq("id", str(memory_id))
            .eq("user_id", user_id)
            .execute()
        )

        return self._to_response(response.data[0]) if response.data else None

    async def get_stats(self, user_id: str) -> MemoryStatsResponse:
        """Get memory statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Memory statistics
        """
        # Get counts by type
        stats = {
            "total_memories": 0,
            "profile_memories": 0,
            "semantic_memories": 0,
            "episodic_memories": 0,
            "procedural_memories": 0,
        }

        for memory_type in MemoryType:
            response = (
                self.supabase.table("memories")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("memory_type", memory_type.value)
                .execute()
            )
            count = response.count or 0
            stats[f"{memory_type.value}_memories"] = count
            stats["total_memories"] += count

        # Get entity count
        entity_response = (
            self.supabase.table("entities")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        stats["total_entities"] = entity_response.count or 0

        # Get relation count
        relation_response = (
            self.supabase.table("entity_relations")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        stats["total_relations"] = relation_response.count or 0

        # Get average reliability
        avg_response = (
            self.supabase.table("memories")
            .select("reliability")
            .eq("user_id", user_id)
            .execute()
        )
        if avg_response.data:
            reliabilities = [m["reliability"] for m in avg_response.data if m.get("reliability")]
            stats["average_reliability"] = sum(reliabilities) / len(reliabilities) if reliabilities else 0

        # Get date range
        oldest_response = (
            self.supabase.table("memories")
            .select("created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )
        if oldest_response.data:
            stats["oldest_memory"] = datetime.fromisoformat(oldest_response.data[0]["created_at"])

        newest_response = (
            self.supabase.table("memories")
            .select("created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if newest_response.data:
            stats["newest_memory"] = datetime.fromisoformat(newest_response.data[0]["created_at"])

        return MemoryStatsResponse(user_id=user_id, **stats)

    async def _keyword_search(
        self,
        user_id: str,
        query: str,
        memory_types: list[MemoryType] | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Perform keyword search on memories.

        Args:
            user_id: User ID
            query: Search query
            memory_types: Type filters
            limit: Maximum results

        Returns:
            List of search results
        """
        # Get memories from Supabase
        supabase_query = (
            self.supabase.table("memories")
            .select("*")
            .eq("user_id", user_id)
        )

        if memory_types:
            supabase_query = supabase_query.in_(
                "memory_type",
                [t.value for t in memory_types]
            )

        response = supabase_query.limit(1000).execute()  # Get more for keyword filtering

        if not response.data:
            return []

        # Apply keyword search
        return self.keyword_search.search(
            query=query,
            documents=response.data,
            limit=limit,
        )

    def _extract_keywords(self, content: str) -> list[str]:
        """Extract keywords from content.

        Args:
            content: Text content

        Returns:
            List of keywords
        """
        # Simple keyword extraction - in production use NLP
        import re
        words = re.findall(r'\b\w{4,}\b', content.lower())
        # Remove common words
        stopwords = {'this', 'that', 'with', 'from', 'have', 'been', 'were', 'they',
                     'their', 'what', 'when', 'where', 'which', 'while', 'about'}
        keywords = [w for w in words if w not in stopwords]
        # Return unique keywords, limited
        return list(dict.fromkeys(keywords))[:20]

    async def _invalidate_cache(self, user_id: str) -> None:
        """Invalidate cached data for user.

        Args:
            user_id: User ID
        """
        try:
            # Delete all cached keys for this user
            pattern = f"memory:{user_id}:*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")

    def _to_response(self, data: dict) -> MemoryResponse:
        """Convert database record to response model.

        Args:
            data: Database record

        Returns:
            MemoryResponse
        """
        return MemoryResponse(
            id=UUID(data["id"]),
            user_id=data["user_id"],
            memory_type=MemoryType(data["memory_type"]),
            content=data["content"],
            keywords=data.get("keywords", []),
            metadata=data.get("metadata", {}),
            reliability=data.get("reliability", 0.5),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"])
                if data.get("last_accessed") else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            # Type-specific fields
            category=data.get("category"),
            attribute=data.get("attribute"),
            value=data.get("value"),
            topic=data.get("topic"),
            subtopic=data.get("subtopic"),
            fact=data.get("fact"),
            conversation_id=UUID(data["conversation_id"]) if data.get("conversation_id") else None,
            event_type=data.get("event_type"),
            summary=data.get("summary"),
            procedure_name=data.get("procedure_name"),
            trigger=data.get("trigger"),
            steps=data.get("steps"),
        )
