"""Qdrant vector database client configuration."""

import logging
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from src.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client instance.

    Returns:
        Configured QdrantClient
    """
    try:
        # Parse URL to determine connection type
        url = settings.qdrant_url

        if url.startswith("http://") or url.startswith("https://"):
            # HTTP connection
            client = QdrantClient(
                url=url,
                api_key=settings.qdrant_api_key,
                timeout=30,
            )
        else:
            # Assume host:port format
            parts = url.split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 6333

            client = QdrantClient(
                host=host,
                port=port,
                api_key=settings.qdrant_api_key,
                timeout=30,
            )

        logger.info(f"Qdrant client initialized: {url}")
        return client

    except Exception as e:
        logger.error(f"Failed to initialize Qdrant client: {e}")
        raise


class QdrantManager:
    """Manager for Qdrant operations."""

    def __init__(self, client: QdrantClient | None = None):
        """Initialize the manager.

        Args:
            client: Optional pre-configured client
        """
        self._client = client
        self.collection_name = settings.qdrant_collection_name
        self.vector_size = settings.qdrant_vector_size

    @property
    def client(self) -> QdrantClient:
        """Get or create the client."""
        if self._client is None:
            self._client = get_qdrant_client()
        return self._client

    def ensure_collection_exists(self) -> None:
        """Ensure the memories collection exists with proper schema."""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE,
                    ),
                )

                # Create payload indices for efficient filtering
                self._create_indices()

                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Qdrant collection exists: {self.collection_name}")

        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise

    def _create_indices(self) -> None:
        """Create payload indices for the collection."""
        indices = [
            ("user_id", "keyword"),
            ("type", "keyword"),
            ("created_at", "datetime"),
        ]

        for field_name, field_type in indices:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_type,
                )
                logger.debug(f"Created index on {field_name}")
            except Exception as e:
                logger.warning(f"Could not create index on {field_name}: {e}")

    def upsert_memory(
        self,
        memory_id: str,
        embedding: list[float],
        payload: dict[str, Any],
    ) -> None:
        """Upsert a memory vector.

        Args:
            memory_id: Unique memory ID
            embedding: Vector embedding
            payload: Metadata payload
        """
        point = PointStruct(
            id=memory_id,
            vector=embedding,
            payload=payload,
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
        )

    def upsert_memories_batch(
        self,
        points: list[PointStruct],
        batch_size: int = 100,
    ) -> None:
        """Upsert multiple memory vectors.

        Args:
            points: List of PointStruct objects
            batch_size: Batch size for upsert
        """
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
            )

    def delete_memory(self, memory_id: str) -> None:
        """Delete a memory vector.

        Args:
            memory_id: Memory ID to delete
        """
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[memory_id],
        )

    def delete_user_memories(self, user_id: str) -> None:
        """Delete all memories for a user.

        Args:
            user_id: User ID whose memories to delete
        """
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id),
                    )
                ]
            ),
        )

    def search(
        self,
        user_id: str,
        query_vector: list[float],
        limit: int = 10,
        memory_types: list[str] | None = None,
        score_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors.

        Args:
            user_id: User ID for filtering
            query_vector: Query embedding
            limit: Maximum results
            memory_types: Optional type filter
            score_threshold: Minimum score

        Returns:
            List of search results
        """
        must_conditions = [
            FieldCondition(
                key="user_id",
                match=MatchValue(value=user_id),
            )
        ]

        if memory_types:
            from qdrant_client.models import MatchAny
            must_conditions.append(
                FieldCondition(
                    key="memory_type",
                    match=MatchAny(any=memory_types),
                )
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=Filter(must=must_conditions),
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        )

        return [
            {
                "id": r.id,
                "score": r.score,
                "payload": r.payload,
            }
            for r in results
        ]

    def get_collection_info(self) -> dict[str, Any]:
        """Get collection statistics.

        Returns:
            Collection info dict
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status.value if info.status else "unknown",
            }
        except Exception as e:
            return {"error": str(e)}

    async def check_connection(self) -> bool:
        """Check if Qdrant connection is working.

        Returns:
            True if connection is successful
        """
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant connection check failed: {e}")
            return False


# Singleton instance
_qdrant_manager: QdrantManager | None = None


def get_qdrant_manager() -> QdrantManager:
    """Get the singleton Qdrant manager.

    Returns:
        QdrantManager instance
    """
    global _qdrant_manager

    if _qdrant_manager is None:
        _qdrant_manager = QdrantManager()

    return _qdrant_manager


def init_qdrant() -> None:
    """Initialize Qdrant collection on startup."""
    manager = get_qdrant_manager()
    manager.ensure_collection_exists()
