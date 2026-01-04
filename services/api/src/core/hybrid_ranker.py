"""Hybrid ranking with weighted scoring.

CRITICAL: Implements weighted ranking with:
- keyword_match: 0.35
- vector_similarity: 0.25
- reliability: 0.20
- recency: 0.15
- frequency: 0.05
"""

import logging
from datetime import datetime
from typing import Any, List

from src.config import settings

logger = logging.getLogger(__name__)


class HybridRanker:
    """Hybrid ranking combining multiple signals.

    Uses weighted combination of:
    - Keyword match score (BM25)
    - Vector similarity score (cosine)
    - Reliability score
    - Recency score (time decay)
    - Frequency score (access count)
    """

    def __init__(
        self,
        keyword_weight: float | None = None,
        vector_weight: float | None = None,
        reliability_weight: float | None = None,
        recency_weight: float | None = None,
        frequency_weight: float | None = None,
    ):
        """Initialize ranker with weights.

        Args:
            keyword_weight: Weight for keyword match (default from settings)
            vector_weight: Weight for vector similarity (default from settings)
            reliability_weight: Weight for reliability (default from settings)
            recency_weight: Weight for recency (default from settings)
            frequency_weight: Weight for frequency (default from settings)
        """
        self.keyword_weight = keyword_weight or settings.keyword_match_weight  # 0.35
        self.vector_weight = vector_weight or settings.vector_similarity_weight  # 0.25
        self.reliability_weight = reliability_weight or settings.reliability_weight  # 0.20
        self.recency_weight = recency_weight or settings.recency_weight  # 0.15
        self.frequency_weight = frequency_weight or settings.frequency_weight  # 0.05

        # Validate weights sum to ~1.0
        total = (
            self.keyword_weight +
            self.vector_weight +
            self.reliability_weight +
            self.recency_weight +
            self.frequency_weight
        )
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Ranking weights sum to {total}, expected 1.0")

    def rank(
        self,
        results: List[dict[str, Any]],
        deduplicate: bool = True,
    ) -> List[dict[str, Any]]:
        """Rank results using weighted scoring.

        Args:
            results: List of search results from various strategies
            deduplicate: Whether to remove duplicate memories

        Returns:
            Ranked and optionally deduplicated results
        """
        if not results:
            return []

        # Deduplicate by memory_id
        if deduplicate:
            results = self._deduplicate(results)

        # Calculate hybrid scores
        scored_results = []
        for result in results:
            scores = self._calculate_scores(result)
            result.update(scores)
            scored_results.append(result)

        # Sort by combined score
        scored_results.sort(key=lambda x: x["score"], reverse=True)

        return scored_results

    def _deduplicate(self, results: List[dict[str, Any]]) -> List[dict[str, Any]]:
        """Remove duplicate results, keeping highest-scored version.

        Args:
            results: List of results with potential duplicates

        Returns:
            Deduplicated list
        """
        seen = {}

        for result in results:
            memory_id = result.get("memory_id")
            if not memory_id:
                continue

            if memory_id not in seen:
                seen[memory_id] = result
            else:
                # Keep the one with higher score
                existing_score = seen[memory_id].get("score", 0)
                new_score = result.get("score", 0)
                if new_score > existing_score:
                    # Merge scores from different strategies
                    merged = self._merge_results(seen[memory_id], result)
                    seen[memory_id] = merged

        return list(seen.values())

    def _merge_results(
        self,
        result1: dict[str, Any],
        result2: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge two results for the same memory.

        Takes the max of each score type.

        Args:
            result1: First result
            result2: Second result

        Returns:
            Merged result
        """
        merged = dict(result1)

        # Take max of each score component
        for key in ["keyword_score", "vector_score", "reliability_score",
                    "recency_score", "frequency_score", "score"]:
            val1 = result1.get(key, 0)
            val2 = result2.get(key, 0)
            merged[key] = max(val1, val2)

        # Combine match types
        types = set()
        if result1.get("match_type"):
            types.add(result1["match_type"])
        if result2.get("match_type"):
            types.add(result2["match_type"])
        merged["match_type"] = ",".join(sorted(types)) if len(types) > 1 else (types.pop() if types else "hybrid")

        return merged

    def _calculate_scores(self, result: dict[str, Any]) -> dict[str, Any]:
        """Calculate all score components.

        Args:
            result: Search result

        Returns:
            Dict with all score components and combined score
        """
        # Get raw scores (normalize to 0-1)
        keyword_score = self._normalize_keyword_score(result.get("keyword_score", 0))
        vector_score = self._normalize_vector_score(result.get("vector_score", 0))
        reliability_score = result.get("reliability", 0.5)  # Already 0-1
        recency_score = self._calculate_recency_score(result.get("created_at"))
        frequency_score = self._calculate_frequency_score(result.get("access_count", 0))

        # Calculate weighted combined score
        combined_score = (
            self.keyword_weight * keyword_score +
            self.vector_weight * vector_score +
            self.reliability_weight * reliability_score +
            self.recency_weight * recency_score +
            self.frequency_weight * frequency_score
        )

        return {
            "keyword_score": keyword_score,
            "vector_score": vector_score,
            "reliability_score": reliability_score,
            "recency_score": recency_score,
            "frequency_score": frequency_score,
            "score": combined_score,
        }

    def _normalize_keyword_score(self, score: float) -> float:
        """Normalize BM25 score to 0-1 range.

        BM25 scores can vary widely, so we use a sigmoid-like normalization.

        Args:
            score: Raw BM25 score

        Returns:
            Normalized score (0-1)
        """
        if score <= 0:
            return 0.0

        # Use tanh for smooth normalization
        # Scale factor of 0.2 works well for typical BM25 scores
        import math
        normalized = math.tanh(score * 0.2)

        return min(1.0, max(0.0, normalized))

    def _normalize_vector_score(self, score: float) -> float:
        """Normalize vector similarity score.

        Cosine similarity is already -1 to 1, but we use 0-1 range.

        Args:
            score: Cosine similarity score

        Returns:
            Normalized score (0-1)
        """
        # Convert from [-1, 1] to [0, 1]
        normalized = (score + 1) / 2

        return min(1.0, max(0.0, normalized))

    def _calculate_recency_score(self, created_at: str | datetime | None) -> float:
        """Calculate recency score with time decay.

        Uses exponential decay over 30 days.

        Args:
            created_at: Creation timestamp

        Returns:
            Recency score (0-1)
        """
        if not created_at:
            return 0.5  # Default for unknown

        try:
            if isinstance(created_at, str):
                # Handle ISO format
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

            now = datetime.utcnow()
            if created_at.tzinfo:
                from datetime import timezone
                now = now.replace(tzinfo=timezone.utc)

            age_days = (now - created_at).days

            # Exponential decay with half-life of 30 days
            import math
            decay_rate = math.log(2) / 30  # Half-life of 30 days
            score = math.exp(-decay_rate * age_days)

            return min(1.0, max(0.0, score))

        except Exception as e:
            logger.warning(f"Recency calculation error: {e}")
            return 0.5

    def _calculate_frequency_score(self, access_count: int) -> float:
        """Calculate frequency score based on access count.

        Uses logarithmic scaling to prevent dominance by highly accessed items.

        Args:
            access_count: Number of times accessed

        Returns:
            Frequency score (0-1)
        """
        if access_count <= 0:
            return 0.0

        # Logarithmic scaling: log(1 + count) / log(1 + max_expected)
        # Assuming max expected access count of ~1000
        import math
        max_expected = 1000
        score = math.log(1 + access_count) / math.log(1 + max_expected)

        return min(1.0, max(0.0, score))

    def rerank_with_context(
        self,
        results: List[dict[str, Any]],
        context: dict[str, Any],
    ) -> List[dict[str, Any]]:
        """Rerank results considering conversation context.

        Args:
            results: Pre-ranked results
            context: Conversation context (topics, entities, etc.)

        Returns:
            Reranked results
        """
        if not context:
            return results

        # Extract context signals
        context_topics = set(context.get("topics", []))
        context_entities = set(context.get("entities", []))

        for result in results:
            boost = 0.0

            # Boost for topic match
            result_keywords = set(result.get("keywords", []))
            topic_overlap = len(context_topics.intersection(result_keywords))
            if topic_overlap:
                boost += 0.1 * topic_overlap

            # Boost for entity match
            result_content = result.get("content", "").lower()
            for entity in context_entities:
                if entity.lower() in result_content:
                    boost += 0.05

            # Apply boost (max 0.3)
            result["score"] = min(1.0, result.get("score", 0) + min(0.3, boost))

        # Re-sort
        results.sort(key=lambda x: x["score"], reverse=True)

        return results


class AdaptiveHybridRanker(HybridRanker):
    """Hybrid ranker that adapts weights based on query type."""

    def rank_for_query_type(
        self,
        results: List[dict[str, Any]],
        query_type: str,
    ) -> List[dict[str, Any]]:
        """Rank with query-type-adapted weights.

        Args:
            results: Search results
            query_type: Type of query (recall, question, conversation, etc.)

        Returns:
            Ranked results
        """
        # Adjust weights based on query type
        if query_type == "recall":
            # For recall queries, prioritize recency and keywords
            self.keyword_weight = 0.40
            self.recency_weight = 0.25
            self.vector_weight = 0.15
            self.reliability_weight = 0.15
            self.frequency_weight = 0.05

        elif query_type == "question":
            # For questions, prioritize vector similarity and reliability
            self.vector_weight = 0.35
            self.reliability_weight = 0.30
            self.keyword_weight = 0.20
            self.recency_weight = 0.10
            self.frequency_weight = 0.05

        elif query_type == "conversation":
            # For conversation, balance all signals
            self.keyword_weight = 0.30
            self.vector_weight = 0.25
            self.reliability_weight = 0.20
            self.recency_weight = 0.20
            self.frequency_weight = 0.05

        else:
            # Default weights
            self.keyword_weight = settings.keyword_match_weight
            self.vector_weight = settings.vector_similarity_weight
            self.reliability_weight = settings.reliability_weight
            self.recency_weight = settings.recency_weight
            self.frequency_weight = settings.frequency_weight

        return self.rank(results)
