"""Multi-strategy retrieval service for memory search."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from qdrant_client import QdrantClient
from redis.asyncio import Redis
from supabase import Client as SupabaseClient

from src.config import settings
from src.core.embeddings import get_embedding_service
from src.core.graph_search import GraphSearch
from src.core.keyword_search import KeywordSearch
from src.core.vector_search import VectorSearch
from src.models.chat import QueryAnalysis
from src.models.memory import MemoryType

logger = logging.getLogger(__name__)


class RetrievalService:
    """Multi-strategy retrieval service combining vector, keyword, and graph search."""

    def __init__(
        self,
        supabase: SupabaseClient,
        qdrant: QdrantClient,
        redis: Redis,
    ):
        """Initialize retrieval service with clients."""
        self.supabase = supabase
        self.qdrant = qdrant
        self.redis = redis

        # Initialize search components
        self.embedder = get_embedding_service()
        self.vector_search = VectorSearch(qdrant)
        self.keyword_search = KeywordSearch()
        self.graph_search = GraphSearch(supabase)

    async def multi_strategy_retrieve(
        self,
        user_id: str,
        query: str,
        analysis: QueryAnalysis,
        limit_per_strategy: int = 10,
    ) -> list[dict[str, Any]]:
        """Run multiple retrieval strategies in parallel.

        This is the CRITICAL multi-strategy retrieval using asyncio.gather
        for parallel execution.

        Args:
            user_id: User ID for isolation
            query: Search query
            analysis: Query analysis with intent and keywords
            limit_per_strategy: Max results per strategy

        Returns:
            Combined list of search results from all strategies
        """
        # Determine which memory types to search based on analysis
        memory_types = self._determine_memory_types(analysis)

        # Run all strategies in parallel using asyncio.gather
        results = await asyncio.gather(
            self._vector_retrieval(user_id, query, memory_types, limit_per_strategy),
            self._keyword_retrieval(user_id, analysis.keywords, memory_types, limit_per_strategy),
            self._entity_retrieval(user_id, analysis.entities_mentioned, limit_per_strategy),
            self._profile_retrieval(user_id),
            self._recent_context_retrieval(user_id, limit_per_strategy),
            return_exceptions=True,
        )

        # Combine and process results
        combined_results = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Retrieval strategy {i} failed: {result}")
                continue
            if result:
                combined_results.extend(result)

        logger.info(
            f"Multi-strategy retrieval returned {len(combined_results)} results "
            f"for user {user_id}"
        )

        return combined_results

    def _determine_memory_types(self, analysis: QueryAnalysis) -> list[str]:
        """Determine which memory types to search based on query analysis.

        Args:
            analysis: Query analysis

        Returns:
            List of memory type strings to search
        """
        if analysis.memory_types_needed:
            return analysis.memory_types_needed

        # Default logic based on intent
        intent = analysis.intent.lower()

        if intent == "recall":
            # For recall queries, search all types
            return [t.value for t in MemoryType]
        elif intent == "question":
            # Questions typically need semantic and profile
            return [MemoryType.SEMANTIC.value, MemoryType.PROFILE.value]
        elif intent == "command":
            # Commands might need procedural
            return [MemoryType.PROCEDURAL.value, MemoryType.PROFILE.value]
        else:
            # Conversation - need recent context
            return [MemoryType.EPISODIC.value, MemoryType.SEMANTIC.value]

    async def _vector_retrieval(
        self,
        user_id: str,
        query: str,
        memory_types: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Perform vector similarity search.

        Args:
            user_id: User ID
            query: Search query
            memory_types: Types to filter
            limit: Maximum results

        Returns:
            List of results with vector scores
        """
        try:
            results = await self.vector_search.search(
                user_id=user_id,
                query=query,
                memory_types=memory_types,
                limit=limit,
            )

            # Add match type
            for r in results:
                r["match_type"] = "vector"

            return results

        except Exception as e:
            logger.error(f"Vector retrieval error: {e}")
            return []

    async def _keyword_retrieval(
        self,
        user_id: str,
        keywords: list[str],
        memory_types: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Perform keyword-based search using BM25.

        Args:
            user_id: User ID
            keywords: Extracted keywords
            memory_types: Types to filter
            limit: Maximum results

        Returns:
            List of results with keyword scores
        """
        if not keywords:
            return []

        try:
            # Get memories from Supabase for keyword search
            query = (
                self.supabase.table("memories")
                .select("*")
                .eq("user_id", user_id)
            )

            if memory_types:
                query = query.in_("type", memory_types)

            response = query.limit(1000).execute()

            if not response.data:
                return []

            # Apply BM25 search
            query_string = " ".join(keywords)
            results = self.keyword_search.search(
                query=query_string,
                documents=response.data,
                limit=limit,
            )

            # Add match type
            for r in results:
                r["match_type"] = "keyword"

            return results

        except Exception as e:
            logger.error(f"Keyword retrieval error: {e}")
            return []

    async def _entity_retrieval(
        self,
        user_id: str,
        entities: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Retrieve memories related to mentioned entities.

        Args:
            user_id: User ID
            entities: Entity names mentioned in query
            limit: Maximum results

        Returns:
            List of entity-related results
        """
        if not entities:
            return []

        try:
            results = await self.graph_search.search_by_entities(
                user_id=user_id,
                entity_names=entities,
                limit=limit,
            )

            # Add match type
            for r in results:
                r["match_type"] = "entity"

            return results

        except Exception as e:
            logger.error(f"Entity retrieval error: {e}")
            return []

    async def _profile_retrieval(
        self,
        user_id: str,
    ) -> list[dict[str, Any]]:
        """Always retrieve profile memories for personalization.

        Args:
            user_id: User ID

        Returns:
            List of profile memories
        """
        try:
            response = (
                self.supabase.table("memories")
                .select("*")
                .eq("user_id", user_id)
                .eq("type", MemoryType.PROFILE.value)
                .order("confidence", desc=True)
                .limit(20)
                .execute()
            )

            results = []
            for memory in response.data or []:
                results.append({
                    "memory_id": memory["id"],
                    "content": memory["content"],
                    "memory_type": memory["type"],
                    "reliability": memory.get("confidence", 0.5),
                    "created_at": memory["created_at"],
                    "access_count": memory.get("access_count", 0),
                    "match_type": "profile",
                    "score": memory.get("confidence", 0.5),  # Use confidence as score
                })

            return results

        except Exception as e:
            logger.error(f"Profile retrieval error: {e}")
            return []

    async def _recent_context_retrieval(
        self,
        user_id: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Retrieve recent episodic memories for context.

        Args:
            user_id: User ID
            limit: Maximum results

        Returns:
            List of recent memories
        """
        try:
            response = (
                self.supabase.table("memories")
                .select("*")
                .eq("user_id", user_id)
                .eq("type", MemoryType.EPISODIC.value)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            results = []
            for memory in response.data or []:
                # Calculate recency score
                created_at = datetime.fromisoformat(memory["created_at"])
                age_days = (datetime.utcnow() - created_at).days
                recency_score = max(0, 1 - (age_days / 30))  # Decay over 30 days

                results.append({
                    "memory_id": memory["id"],
                    "content": memory["content"],
                    "memory_type": memory["type"],
                    "reliability": memory.get("confidence", 0.5),
                    "created_at": memory["created_at"],
                    "access_count": memory.get("access_count", 0),
                    "match_type": "recent",
                    "recency_score": recency_score,
                    "score": recency_score * memory.get("confidence", 0.5),
                })

            return results

        except Exception as e:
            logger.error(f"Recent context retrieval error: {e}")
            return []

    async def retrieve_for_context(
        self,
        user_id: str,
        query: str,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Simplified retrieval for context building.

        Args:
            user_id: User ID
            query: Search query
            max_results: Maximum total results

        Returns:
            Combined retrieval results
        """
        # Create a simple analysis
        analysis = QueryAnalysis(
            original_query=query,
            intent="conversation",
            keywords=self._extract_simple_keywords(query),
            entities_mentioned=[],
            requires_memory=True,
        )

        return await self.multi_strategy_retrieve(
            user_id=user_id,
            query=query,
            analysis=analysis,
            limit_per_strategy=max_results // 5,  # Divide among strategies
        )

    def _extract_simple_keywords(self, text: str) -> list[str]:
        """Simple keyword extraction.

        Args:
            text: Input text

        Returns:
            List of keywords
        """
        import re
        words = re.findall(r'\b\w{4,}\b', text.lower())
        stopwords = {'this', 'that', 'with', 'from', 'have', 'been', 'were', 'they',
                     'their', 'what', 'when', 'where', 'which', 'while', 'about',
                     'would', 'could', 'should', 'please', 'thank', 'thanks'}
        return [w for w in words if w not in stopwords][:10]


class CachedRetrievalService(RetrievalService):
    """Retrieval service with Redis caching."""

    async def multi_strategy_retrieve(
        self,
        user_id: str,
        query: str,
        analysis: QueryAnalysis,
        limit_per_strategy: int = 10,
    ) -> list[dict[str, Any]]:
        """Cached multi-strategy retrieval.

        Args:
            user_id: User ID
            query: Search query
            analysis: Query analysis
            limit_per_strategy: Max per strategy

        Returns:
            Cached or fresh results
        """
        import hashlib
        import json

        # Create cache key
        cache_key = f"retrieval:{user_id}:{hashlib.md5(query.encode()).hexdigest()}"

        try:
            # Try cache first
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")

        # Get fresh results
        results = await super().multi_strategy_retrieve(
            user_id=user_id,
            query=query,
            analysis=analysis,
            limit_per_strategy=limit_per_strategy,
        )

        try:
            # Cache results
            await self.redis.setex(
                cache_key,
                settings.redis_cache_ttl,
                json.dumps(results, default=str),
            )
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

        return results
