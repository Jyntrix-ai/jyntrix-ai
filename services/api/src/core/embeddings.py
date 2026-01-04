"""Embedding service using sentence-transformers (all-MiniLM-L6-v2, 384 dims)."""

import logging
from functools import lru_cache
from typing import List

import numpy as np

from src.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding service using sentence-transformers.

    Uses all-MiniLM-L6-v2 model which produces 384-dimensional embeddings.
    This is a lightweight but effective model for semantic similarity.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embedding service.

        Args:
            model_name: Name of the sentence-transformers model to use
        """
        self.model_name = model_name
        self.model = None
        self.dimensions = 384  # all-MiniLM-L6-v2 output dimensions
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy load the model on first use."""
        if self._initialized:
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self._initialized = True
            logger.info(f"Embedding model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise RuntimeError(f"Could not initialize embedding model: {e}")

    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            List of 384 floats representing the embedding
        """
        self._ensure_initialized()

        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.dimensions

        try:
            # Generate embedding
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True,  # L2 normalize for cosine similarity
            )

            return embedding.tolist()

        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            batch_size: Batch size for processing

        Returns:
            List of embeddings
        """
        self._ensure_initialized()

        if not texts:
            return []

        try:
            # Filter and track empty texts
            non_empty_indices = []
            non_empty_texts = []

            for i, text in enumerate(texts):
                if text and text.strip():
                    non_empty_indices.append(i)
                    non_empty_texts.append(text)

            # Generate embeddings for non-empty texts
            if non_empty_texts:
                embeddings = self.model.encode(
                    non_empty_texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    batch_size=batch_size,
                    show_progress_bar=False,
                )
            else:
                embeddings = np.array([])

            # Reconstruct full list with zero vectors for empty texts
            result = []
            embedding_idx = 0

            for i in range(len(texts)):
                if i in non_empty_indices:
                    result.append(embeddings[embedding_idx].tolist())
                    embedding_idx += 1
                else:
                    result.append([0.0] * self.dimensions)

            return result

        except Exception as e:
            logger.error(f"Batch embedding error: {e}")
            raise

    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Cosine similarity score (0-1 for normalized vectors)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # For normalized vectors, cosine similarity is just dot product
        return float(np.dot(vec1, vec2))

    def find_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 10,
    ) -> List[tuple[int, float]]:
        """Find most similar embeddings from candidates.

        Args:
            query_embedding: Query vector
            candidate_embeddings: List of candidate vectors
            top_k: Number of top results to return

        Returns:
            List of (index, similarity_score) tuples
        """
        if not candidate_embeddings:
            return []

        query = np.array(query_embedding)
        candidates = np.array(candidate_embeddings)

        # Calculate similarities (dot product for normalized vectors)
        similarities = np.dot(candidates, query)

        # Get top-k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        return [(int(i), float(similarities[i])) for i in top_indices]


# Singleton instance
_embedding_service: EmbeddingService | None = None


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Get the singleton embedding service instance.

    Returns:
        Configured EmbeddingService
    """
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = EmbeddingService(
            model_name=settings.embedding_model
        )

    return _embedding_service


def embed_text(text: str) -> List[float]:
    """Convenience function to embed text.

    Args:
        text: Text to embed

    Returns:
        Embedding vector
    """
    return get_embedding_service().embed(text)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Convenience function to embed multiple texts.

    Args:
        texts: List of texts

    Returns:
        List of embedding vectors
    """
    return get_embedding_service().embed_batch(texts)
