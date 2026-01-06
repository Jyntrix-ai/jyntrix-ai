"""Vector search using Qdrant with user_id PRE-filtering."""

import asyncio
import logging
from typing import Any, List

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

from src.config import settings
from src.core.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class VectorSearch:
    """Vector similarity search using Qdrant.

    CRITICAL: All searches use user_id PRE-filtering to ensure
    strict data isolation between users.
    """

    # Class-level embedding cache for repeated queries
    _embedding_cache: dict[str, list] = {}
    _cache_max_size: int = 100

    def __init__(self, client: QdrantClient):
        """Initialize vector search with Qdrant client.

        Args:
            client: Configured Qdrant client
        """
        self.client = client
        self.collection_name = settings.qdrant_collection_name
        self.embedder = get_embedding_service()

    async def search(
        self,
        user_id: str,
        query: str,
        memory_types: List[str] | None = None,
        limit: int = 10,
        score_threshold: float = 0.0,
    ) -> List[dict[str, Any]]:
        """Search for similar vectors with user isolation.

        CRITICAL: Uses user_id as a PRE-filter (must condition) to ensure
        users can only access their own memories.

        Args:
            user_id: User ID for isolation (REQUIRED)
            query: Search query text
            memory_types: Optional list of memory types to filter
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of search results with scores
        """
        # Generate embedding for query (cached and non-blocking)
        cache_key = f"{user_id}:{query}"
        if cache_key in self._embedding_cache:
            query_embedding = self._embedding_cache[cache_key]
        else:
            # Run embedding in thread pool to avoid blocking event loop
            query_embedding = await asyncio.to_thread(self.embedder.embed, query)
            # Cache the embedding
            self._embedding_cache[cache_key] = query_embedding
            # Limit cache size (simple FIFO eviction)
            if len(self._embedding_cache) > self._cache_max_size:
                oldest_key = next(iter(self._embedding_cache))
                del self._embedding_cache[oldest_key]

        # Build filter conditions - user_id is REQUIRED
        must_conditions = [
            FieldCondition(
                key="user_id",
                match=MatchValue(value=user_id),
            )
        ]

        # Add memory type filter if specified
        if memory_types:
            must_conditions.append(
                FieldCondition(
                    key="type",
                    match=MatchAny(any=memory_types),
                )
            )

        # Create filter
        search_filter = Filter(must=must_conditions)

        try:
            # Perform search with pre-filtering using query_points (new API)
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
            )

            # Convert to standard format
            search_results = []
            for result in results.points:
                search_results.append({
                    "memory_id": result.id,
                    "vector_score": result.score,
                    "score": result.score,  # For hybrid ranking
                    "content": result.payload.get("content", ""),
                    "memory_type": result.payload.get("type", ""),
                    "keywords": result.payload.get("keywords", []),
                    "reliability": result.payload.get("confidence", 0.5),
                    "created_at": result.payload.get("created_at", ""),
                    "match_type": "vector",
                })

            logger.debug(
                f"Vector search for user {user_id}: "
                f"{len(search_results)} results for query '{query[:50]}...'"
            )

            return search_results

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    async def search_by_embedding(
        self,
        user_id: str,
        embedding: List[float],
        memory_types: List[str] | None = None,
        limit: int = 10,
        score_threshold: float = 0.0,
    ) -> List[dict[str, Any]]:
        """Search using a pre-computed embedding.

        Args:
            user_id: User ID for isolation
            embedding: Pre-computed query embedding
            memory_types: Optional memory type filter
            limit: Maximum results
            score_threshold: Minimum score

        Returns:
            List of search results
        """
        # Build filter
        must_conditions = [
            FieldCondition(
                key="user_id",
                match=MatchValue(value=user_id),
            )
        ]

        if memory_types:
            must_conditions.append(
                FieldCondition(
                    key="type",
                    match=MatchAny(any=memory_types),
                )
            )

        search_filter = Filter(must=must_conditions)

        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=embedding,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
            )

            return [
                {
                    "memory_id": r.id,
                    "vector_score": r.score,
                    "score": r.score,
                    "content": r.payload.get("content", ""),
                    "memory_type": r.payload.get("type", ""),
                    "keywords": r.payload.get("keywords", []),
                    "reliability": r.payload.get("confidence", 0.5),
                    "created_at": r.payload.get("created_at", ""),
                    "match_type": "vector",
                }
                for r in results.points
            ]

        except Exception as e:
            logger.error(f"Vector search by embedding error: {e}")
            return []

    async def find_similar_memories(
        self,
        user_id: str,
        memory_id: str,
        limit: int = 5,
        exclude_self: bool = True,
    ) -> List[dict[str, Any]]:
        """Find memories similar to a given memory.

        Args:
            user_id: User ID for isolation
            memory_id: ID of the reference memory
            limit: Maximum results
            exclude_self: Whether to exclude the reference memory

        Returns:
            List of similar memories
        """
        try:
            # Get the reference memory's vector
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[memory_id],
                with_vectors=True,
            )

            if not result:
                return []

            reference_vector = result[0].vector

            # Search for similar
            results = await self.search_by_embedding(
                user_id=user_id,
                embedding=reference_vector,
                limit=limit + 1 if exclude_self else limit,
            )

            # Optionally exclude self
            if exclude_self:
                results = [r for r in results if r["memory_id"] != memory_id][:limit]

            return results

        except Exception as e:
            logger.error(f"Find similar memories error: {e}")
            return []

    async def batch_search(
        self,
        user_id: str,
        queries: List[str],
        limit_per_query: int = 5,
    ) -> List[List[dict[str, Any]]]:
        """Perform batch search for multiple queries.

        Args:
            user_id: User ID for isolation
            queries: List of search queries
            limit_per_query: Results per query

        Returns:
            List of result lists, one per query
        """
        results = []

        for query in queries:
            query_results = await self.search(
                user_id=user_id,
                query=query,
                limit=limit_per_query,
            )
            results.append(query_results)

        return results

    def ensure_collection_exists(self) -> None:
        """Ensure the Qdrant collection exists with proper configuration."""
        from qdrant_client.models import Distance, VectorParams

        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                # Create collection
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=settings.qdrant_vector_size,  # 384 for all-MiniLM-L6-v2
                        distance=Distance.COSINE,
                    ),
                )

                # Create payload index for user_id (critical for filtering)
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="user_id",
                    field_schema="keyword",
                )

                # Create index for memory_type
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="memory_type",
                    field_schema="keyword",
                )

                logger.info(f"Created Qdrant collection: {self.collection_name}")

        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise

    def get_collection_info(self) -> dict[str, Any]:
        """Get information about the collection.

        Returns:
            Collection info dict
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": info.status.value if info.status else "unknown",
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {"error": str(e)}
