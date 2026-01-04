"""
Supabase Client Wrapper

Provides async-compatible wrapper for Supabase operations on memories,
entities, and entity relations tables.
"""

from datetime import UTC, datetime
from enum import Enum
from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from src.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryType(str, Enum):
    """Types of memories in the system."""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class EmbeddingStatus(str, Enum):
    """Status of embedding generation for a memory."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SupabaseClient:
    """Wrapper for Supabase database operations."""

    def __init__(self, client: Client) -> None:
        self._client = client

    # ----- Memory Operations -----

    async def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        """
        Fetch a memory record by ID.

        Args:
            memory_id: UUID of the memory.

        Returns:
            Memory record dict or None if not found.
        """
        try:
            response = (
                self._client.table("memories")
                .select("*")
                .eq("id", memory_id)
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Failed to fetch memory {memory_id}: {e}")
            return None

    async def update_memory_embedding_status(
        self,
        memory_id: str,
        status: EmbeddingStatus,
        error_message: str | None = None,
    ) -> bool:
        """
        Update the embedding status of a memory.

        Args:
            memory_id: UUID of the memory.
            status: New embedding status.
            error_message: Optional error message if status is FAILED.

        Returns:
            True if update succeeded, False otherwise.
        """
        try:
            update_data: dict[str, Any] = {
                "embedding_status": status.value,
                "updated_at": datetime.now(UTC).isoformat(),
            }
            if error_message:
                update_data["embedding_error"] = error_message

            self._client.table("memories").update(update_data).eq(
                "id", memory_id
            ).execute()
            logger.info(f"Updated memory {memory_id} embedding status to {status.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id} embedding status: {e}")
            return False

    async def create_memory(
        self,
        user_id: str,
        content: str,
        memory_type: MemoryType,
        source_type: str = "extraction",
        source_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Create a new memory record.

        Args:
            user_id: UUID of the user who owns this memory.
            content: The memory content/text.
            memory_type: Type of memory (episodic, semantic, procedural).
            source_type: Where this memory originated from.
            source_id: Optional ID of the source message.
            metadata: Optional metadata dict.

        Returns:
            Created memory record or None on failure.
        """
        try:
            data = {
                "user_id": user_id,
                "content": content,
                "type": memory_type.value,
                "source_message_id": source_id,  # Use correct column name
                "metadata": metadata or {},
                "embedding_status": EmbeddingStatus.PENDING.value,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
            response = self._client.table("memories").insert(data).execute()
            if response.data:
                logger.info(f"Created memory {response.data[0]['id']} for user {user_id}")
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to create memory for user {user_id}: {e}")
            return None

    # ----- Message Operations -----

    async def get_message(self, message_id: str) -> dict[str, Any] | None:
        """
        Fetch a message record by ID.

        Args:
            message_id: UUID of the message.

        Returns:
            Message record dict or None if not found.
        """
        try:
            response = (
                self._client.table("messages")
                .select("*")
                .eq("id", message_id)
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Failed to fetch message {message_id}: {e}")
            return None

    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Fetch messages for a conversation, ordered by creation time.

        Args:
            conversation_id: UUID of the conversation.
            limit: Maximum number of messages to fetch.

        Returns:
            List of message records.
        """
        try:
            response = (
                self._client.table("messages")
                .select("*")
                .eq("conversation_id", conversation_id)
                .order("created_at", desc=False)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to fetch messages for conversation {conversation_id}: {e}")
            return []

    # ----- Entity Operations -----

    async def create_entity(
        self,
        user_id: str,
        name: str,
        entity_type: str,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Create or update an entity record.

        Uses upsert to handle duplicate entities for the same user.

        Args:
            user_id: UUID of the user who owns this entity.
            name: Name of the entity.
            entity_type: Type of entity (person, location, org, date, etc.).
            description: Optional description.
            metadata: Optional metadata dict.

        Returns:
            Entity record or None on failure.
        """
        try:
            # Normalize the name for matching
            normalized_name = name.lower().strip()

            data = {
                "user_id": user_id,
                "name": name,
                "type": entity_type,
                "normalized_name": normalized_name,
                "description": description,
                "metadata": metadata or {},
                "updated_at": datetime.now(UTC).isoformat(),
            }

            # Check if entity already exists for this user
            existing = (
                self._client.table("entities")
                .select("*")
                .eq("user_id", user_id)
                .eq("normalized_name", normalized_name)
                .eq("type", entity_type)
                .execute()
            )

            if existing.data:
                # Update existing entity - increment mention count
                entity_id = existing.data[0]["id"]
                update_data = {
                    "description": description or existing.data[0].get("description"),
                    "mention_count": existing.data[0].get("mention_count", 1) + 1,
                    "last_mentioned_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
                response = (
                    self._client.table("entities")
                    .update(update_data)
                    .eq("id", entity_id)
                    .execute()
                )
                logger.info(f"Updated entity {entity_id} for user {user_id}")
                return existing.data[0]  # Return existing entity with ID
            else:
                # Create new entity
                data["created_at"] = datetime.now(UTC).isoformat()
                data["mention_count"] = 1
                data["last_mentioned_at"] = datetime.now(UTC).isoformat()
                response = self._client.table("entities").insert(data).execute()
                logger.info(f"Created entity '{name}' of type '{entity_type}' for user {user_id}")
                return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to create/update entity for user {user_id}: {e}")
            return None

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch an entity by ID."""
        try:
            response = (
                self._client.table("entities")
                .select("*")
                .eq("id", entity_id)
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Failed to fetch entity {entity_id}: {e}")
            return None

    # ----- Entity Relation Operations -----

    async def create_entity_relation(
        self,
        user_id: str,
        source_entity_id: str,
        target_entity_id: str,
        relation_type: str,
        description: str | None = None,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Create a relation between two entities.

        Args:
            user_id: UUID of the user who owns this relation.
            source_entity_id: UUID of the source entity.
            target_entity_id: UUID of the target entity.
            relation_type: Type of relation (works_at, lives_in, knows, etc.).
            description: Optional description of the relation.
            confidence: Confidence score (0.0 to 1.0).
            metadata: Optional metadata dict.

        Returns:
            Relation record or None on failure.
        """
        try:
            data = {
                "user_id": user_id,
                "source_entity_id": source_entity_id,
                "target_entity_id": target_entity_id,
                "relation_type": relation_type,
                "description": description,
                "confidence": confidence,
                "metadata": metadata or {},
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }

            response = self._client.table("entity_relations").insert(data).execute()
            if response.data:
                logger.info(
                    f"Created relation {relation_type} between {source_entity_id} "
                    f"and {target_entity_id}"
                )
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to create entity relation: {e}")
            return None

    # ----- Conversation Operations -----

    async def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        """Fetch a conversation by ID."""
        try:
            response = (
                self._client.table("conversations")
                .select("*")
                .eq("id", conversation_id)
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Failed to fetch conversation {conversation_id}: {e}")
            return None

    async def update_conversation_summary(
        self,
        conversation_id: str,
        summary: str,
        summary_memory_id: str | None = None,
    ) -> bool:
        """
        Update a conversation with its summary.

        Args:
            conversation_id: UUID of the conversation.
            summary: Generated summary text.
            summary_memory_id: Optional ID of the created summary memory.

        Returns:
            True if update succeeded, False otherwise.
        """
        try:
            update_data = {
                "summary": summary,
                "summarized_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
            if summary_memory_id:
                update_data["summary_memory_id"] = summary_memory_id

            self._client.table("conversations").update(update_data).eq(
                "id", conversation_id
            ).execute()
            logger.info(f"Updated summary for conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update conversation summary: {e}")
            return False


@lru_cache
def get_supabase_client() -> SupabaseClient:
    """Get cached Supabase client instance."""
    client = create_client(
        config.supabase_url,
        config.supabase_service_key.get_secret_value(),
    )
    return SupabaseClient(client)
