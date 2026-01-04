"""
Embedding Generation Task

Generates embeddings for memories and messages using sentence-transformers.
Stores vectors in Qdrant with tenant isolation via user_id payload.
"""

from typing import Any

from sentence_transformers import SentenceTransformer

from src.config import config
from src.db.supabase import EmbeddingStatus, get_supabase_client
from src.db.qdrant import get_qdrant_client
from src.utils.logger import TaskLogger, get_logger

logger = get_logger(__name__)

# Lazy-loaded embedding model (loaded once per worker process)
_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Get or create the embedding model instance."""
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {config.embedding_model}")
        _embedding_model = SentenceTransformer(config.embedding_model)
        logger.info(
            f"Embedding model loaded. Dimension: {_embedding_model.get_sentence_embedding_dimension()}"
        )
    return _embedding_model


async def generate_embedding(
    ctx: dict[str, Any],
    memory_id: str,
) -> dict[str, Any]:
    """
    Generate embedding for a memory and store in Qdrant.

    This task:
    1. Fetches the memory from Supabase by ID
    2. Generates embedding using sentence-transformers (all-MiniLM-L6-v2, 384 dims)
    3. Stores the vector in Qdrant with user_id payload for tenant isolation
    4. Updates memory.embedding_status = 'completed' in Supabase

    Args:
        ctx: ARQ context containing Redis pool and other shared resources.
        memory_id: UUID of the memory to embed.

    Returns:
        Result dict with status and metadata.
    """
    supabase = get_supabase_client()
    qdrant = get_qdrant_client()

    with TaskLogger(logger, "generate_embedding", memory_id=memory_id):
        try:
            # Step 1: Fetch memory from Supabase
            memory = await supabase.get_memory(memory_id)
            if not memory:
                logger.error(f"Memory {memory_id} not found")
                return {
                    "success": False,
                    "memory_id": memory_id,
                    "error": "Memory not found",
                }

            user_id = memory.get("user_id")
            content = memory.get("content")
            memory_type = memory.get("type", "semantic")

            if not content:
                logger.error(f"Memory {memory_id} has no content")
                await supabase.update_memory_embedding_status(
                    memory_id,
                    EmbeddingStatus.FAILED,
                    "Memory has no content",
                )
                return {
                    "success": False,
                    "memory_id": memory_id,
                    "error": "Memory has no content",
                }

            # Update status to processing
            await supabase.update_memory_embedding_status(
                memory_id,
                EmbeddingStatus.PROCESSING,
            )

            # Step 2: Generate embedding
            model = get_embedding_model()
            embedding = model.encode(content, convert_to_numpy=True).tolist()

            logger.debug(
                f"Generated embedding for memory {memory_id}: "
                f"{len(embedding)} dimensions"
            )

            # Step 3: Store vector in Qdrant with tenant isolation
            success = await qdrant.upsert_vector(
                memory_id=memory_id,
                vector=embedding,
                user_id=user_id,
                memory_type=memory_type,
                content=content,
                confidence=memory.get("confidence", 1.0),
                metadata=memory.get("metadata"),
            )

            if not success:
                await supabase.update_memory_embedding_status(
                    memory_id,
                    EmbeddingStatus.FAILED,
                    "Failed to store vector in Qdrant",
                )
                return {
                    "success": False,
                    "memory_id": memory_id,
                    "error": "Failed to store vector in Qdrant",
                }

            # Step 4: Update embedding status to completed
            await supabase.update_memory_embedding_status(
                memory_id,
                EmbeddingStatus.COMPLETED,
            )

            logger.info(
                f"Successfully generated and stored embedding for memory {memory_id}"
            )

            return {
                "success": True,
                "memory_id": memory_id,
                "user_id": user_id,
                "embedding_dimension": len(embedding),
                "memory_type": memory_type,
            }

        except Exception as e:
            logger.exception(f"Failed to generate embedding for memory {memory_id}: {e}")

            # Update status to failed
            await supabase.update_memory_embedding_status(
                memory_id,
                EmbeddingStatus.FAILED,
                str(e),
            )

            return {
                "success": False,
                "memory_id": memory_id,
                "error": str(e),
            }


async def generate_batch_embeddings(
    ctx: dict[str, Any],
    memory_ids: list[str],
) -> dict[str, Any]:
    """
    Generate embeddings for multiple memories in a batch.

    More efficient than individual calls for bulk processing.

    Args:
        ctx: ARQ context.
        memory_ids: List of memory UUIDs to embed.

    Returns:
        Result dict with success/failure counts and details.
    """
    supabase = get_supabase_client()
    qdrant = get_qdrant_client()
    model = get_embedding_model()

    results = {
        "total": len(memory_ids),
        "successful": 0,
        "failed": 0,
        "errors": [],
    }

    with TaskLogger(logger, "generate_batch_embeddings"):
        # Fetch all memories
        memories = []
        for memory_id in memory_ids:
            memory = await supabase.get_memory(memory_id)
            if memory and memory.get("content"):
                memories.append(memory)
            else:
                results["failed"] += 1
                results["errors"].append({
                    "memory_id": memory_id,
                    "error": "Memory not found or has no content",
                })

        if not memories:
            return results

        try:
            # Batch encode all contents
            contents = [m["content"] for m in memories]
            embeddings = model.encode(
                contents,
                batch_size=config.embedding_batch_size,
                convert_to_numpy=True,
            ).tolist()

            # Store each embedding
            for memory, embedding in zip(memories, embeddings):
                memory_id = memory["id"]
                try:
                    success = await qdrant.upsert_vector(
                        memory_id=memory_id,
                        vector=embedding,
                        user_id=memory["user_id"],
                        memory_type=memory.get("type", "semantic"),
                        content=memory["content"],
                        metadata=memory.get("metadata"),
                    )

                    if success:
                        await supabase.update_memory_embedding_status(
                            memory_id,
                            EmbeddingStatus.COMPLETED,
                        )
                        results["successful"] += 1
                    else:
                        await supabase.update_memory_embedding_status(
                            memory_id,
                            EmbeddingStatus.FAILED,
                            "Failed to store in Qdrant",
                        )
                        results["failed"] += 1
                        results["errors"].append({
                            "memory_id": memory_id,
                            "error": "Failed to store in Qdrant",
                        })

                except Exception as e:
                    await supabase.update_memory_embedding_status(
                        memory_id,
                        EmbeddingStatus.FAILED,
                        str(e),
                    )
                    results["failed"] += 1
                    results["errors"].append({
                        "memory_id": memory_id,
                        "error": str(e),
                    })

        except Exception as e:
            logger.exception(f"Batch embedding generation failed: {e}")
            # Mark all remaining as failed
            for memory in memories:
                if not any(err["memory_id"] == memory["id"] for err in results["errors"]):
                    await supabase.update_memory_embedding_status(
                        memory["id"],
                        EmbeddingStatus.FAILED,
                        str(e),
                    )
                    results["failed"] += 1
                    results["errors"].append({
                        "memory_id": memory["id"],
                        "error": str(e),
                    })

        logger.info(
            f"Batch embedding completed: {results['successful']}/{results['total']} successful"
        )
        return results
