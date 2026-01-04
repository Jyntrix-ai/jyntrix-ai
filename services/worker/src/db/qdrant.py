"""
Qdrant Client Wrapper

Provides async-compatible wrapper for Qdrant vector database operations.
Handles vector storage with tenant isolation via user_id payload filtering.
"""

import uuid
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient as QdrantClientBase
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams

from src.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class QdrantClient:
    """Wrapper for Qdrant vector database operations."""

    def __init__(self, client: QdrantClientBase) -> None:
        self._client = client
        self._collection = config.qdrant_collection
        self._dimension = config.embedding_dimension

    async def ensure_collection_exists(self) -> bool:
        """
        Ensure the memories collection exists with proper configuration.

        Returns:
            True if collection exists or was created successfully.
        """
        try:
            collections = self._client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self._collection not in collection_names:
                self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config=VectorParams(
                        size=self._dimension,
                        distance=Distance.COSINE,
                    ),
                    # Optimized for filtering by user_id (tenant isolation)
                    optimizers_config=models.OptimizersConfigDiff(
                        indexing_threshold=10000,
                    ),
                )

                # Create payload index for efficient user_id filtering
                self._client.create_payload_index(
                    collection_name=self._collection,
                    field_name="user_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )

                # Create payload index for type filtering
                self._client.create_payload_index(
                    collection_name=self._collection,
                    field_name="type",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )

                logger.info(f"Created Qdrant collection '{self._collection}'")

            return True
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            return False

    async def upsert_vector(
        self,
        memory_id: str,
        vector: list[float],
        user_id: str,
        memory_type: str,
        content: str | None = None,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Store or update a vector for a memory.

        Args:
            memory_id: UUID of the memory (used as point ID).
            vector: Embedding vector (384 dimensions for all-MiniLM-L6-v2).
            user_id: UUID of the user (for tenant isolation).
            memory_type: Type of memory (episodic, semantic, procedural).
            content: Optional content text for payload.
            confidence: Confidence score for hybrid ranking.
            metadata: Optional additional metadata.

        Returns:
            True if upsert succeeded, False otherwise.
        """
        try:
            # Ensure collection exists before upserting
            await self.ensure_collection_exists()

            # Build payload with tenant isolation
            payload: dict[str, Any] = {
                "user_id": user_id,
                "memory_id": memory_id,
                "type": memory_type,  # Match database column name
                "confidence": confidence,  # For hybrid ranking
            }
            if content:
                payload["content"] = content[:500]  # Truncate for storage
            if metadata:
                payload["metadata"] = metadata

            # Use memory_id as the point ID (convert UUID to int hash for Qdrant)
            point_id = str(uuid.UUID(memory_id))

            self._client.upsert(
                collection_name=self._collection,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload,
                    )
                ],
            )

            logger.info(f"Upserted vector for memory {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert vector for memory {memory_id}: {e}")
            return False

    async def search_similar(
        self,
        vector: list[float],
        user_id: str,
        limit: int = 10,
        memory_type: str | None = None,
        score_threshold: float = 0.7,
    ) -> list[dict[str, Any]]:
        """
        Search for similar vectors with tenant isolation.

        Args:
            vector: Query embedding vector.
            user_id: UUID of the user (enforces tenant isolation).
            limit: Maximum number of results.
            memory_type: Optional filter by memory type.
            score_threshold: Minimum similarity score (0.0 to 1.0).

        Returns:
            List of matching results with scores and payloads.
        """
        try:
            # Build filter for tenant isolation
            must_conditions: list[models.Condition] = [
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id),
                )
            ]

            if memory_type:
                must_conditions.append(
                    models.FieldCondition(
                        key="type",
                        match=models.MatchValue(value=memory_type),
                    )
                )

            query_filter = models.Filter(must=must_conditions)

            results = self._client.search(
                collection_name=self._collection,
                query_vector=vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
            )

            return [
                {
                    "memory_id": hit.payload.get("memory_id") if hit.payload else None,
                    "score": hit.score,
                    "content": hit.payload.get("content") if hit.payload else None,
                    "type": hit.payload.get("type") if hit.payload else None,
                    "metadata": hit.payload.get("metadata") if hit.payload else None,
                }
                for hit in results
            ]
        except Exception as e:
            logger.error(f"Failed to search similar vectors: {e}")
            return []

    async def delete_vector(self, memory_id: str) -> bool:
        """
        Delete a vector by memory ID.

        Args:
            memory_id: UUID of the memory to delete.

        Returns:
            True if deletion succeeded, False otherwise.
        """
        try:
            point_id = str(uuid.UUID(memory_id))
            self._client.delete(
                collection_name=self._collection,
                points_selector=models.PointIdsList(
                    points=[point_id],
                ),
            )
            logger.info(f"Deleted vector for memory {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vector for memory {memory_id}: {e}")
            return False

    async def delete_user_vectors(self, user_id: str) -> bool:
        """
        Delete all vectors for a user (for GDPR compliance).

        Args:
            user_id: UUID of the user.

        Returns:
            True if deletion succeeded, False otherwise.
        """
        try:
            self._client.delete(
                collection_name=self._collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="user_id",
                                match=models.MatchValue(value=user_id),
                            )
                        ]
                    )
                ),
            )
            logger.info(f"Deleted all vectors for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors for user {user_id}: {e}")
            return False

    async def get_collection_info(self) -> dict[str, Any] | None:
        """Get information about the memories collection."""
        try:
            info = self._client.get_collection(self._collection)
            return {
                "name": info.config.params.vectors.size if info.config else None,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status.value if info.status else None,
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return None


@lru_cache
def get_qdrant_client() -> QdrantClient:
    """Get cached Qdrant client instance."""
    client = QdrantClientBase(
        url=config.qdrant_url,
        api_key=config.qdrant_api_key.get_secret_value() if config.qdrant_api_key else None,
    )
    return QdrantClient(client)
