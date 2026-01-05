"""Chat service - Main orchestrator for chat functionality.

This is the CRITICAL service that handles:
1. Save message to Supabase
2. Analyze query
3. Multi-strategy retrieval (parallel with asyncio.gather)
4. Hybrid ranking
5. Context assembly
6. Stream LLM response
7. Save assistant response
8. Enqueue ARQ task for memory extraction

Analytics instrumentation tracks timing for each phase.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, AsyncGenerator
from uuid import UUID, uuid4

from qdrant_client import QdrantClient
from redis.asyncio import Redis
from supabase import Client as SupabaseClient

from src.analytics import (
    AnalyticsCollector,
    QueryAnalysisMetrics,
    emit_analytics,
    get_collector,
    set_collector,
    track_span,
)
from src.config import settings
from src.core.context_builder import ContextBuilder
from src.core.hybrid_ranker import HybridRanker
from src.core.llm_client import LLMClient
from src.core.query_analyzer import QueryAnalyzer
from src.models.chat import Conversation, Message, MessageRole, QueryAnalysis
from src.models.memory import MemoryContext
from src.schemas.chat import (
    ChatCompletionResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
)
from src.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class ChatService:
    """Chat service for handling conversations and message streaming."""

    def __init__(
        self,
        supabase: SupabaseClient,
        qdrant: QdrantClient,
        redis: Redis,
    ):
        """Initialize chat service with required clients."""
        self.supabase = supabase
        self.qdrant = qdrant
        self.redis = redis

        # Initialize sub-services
        self.query_analyzer = QueryAnalyzer()
        self.retrieval_service = RetrievalService(supabase, qdrant, redis)
        self.hybrid_ranker = HybridRanker()
        self.context_builder = ContextBuilder()
        self.llm_client = LLMClient()

    async def send_message_stream(
        self,
        user_id: str,
        content: str,
        conversation_id: UUID | None = None,
        include_memory: bool = True,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Send a message and stream the response.

        This is the main orchestration flow:
        1. Save user message to Supabase
        2. Analyze query intent
        3. Run multi-strategy retrieval in parallel
        4. Apply hybrid ranking
        5. Build context within token budget
        6. Stream LLM response
        7. Save assistant response
        8. Enqueue memory extraction task

        Analytics instrumentation tracks timing for each phase.

        Args:
            user_id: Current user ID
            content: Message content
            conversation_id: Optional existing conversation ID
            include_memory: Whether to include memory context

        Yields:
            Stream chunks with type, content, and metadata
        """
        start_time = time.time()

        # Initialize analytics collector
        collector: AnalyticsCollector | None = None
        if settings.analytics_enabled:
            collector = AnalyticsCollector(
                request_id=str(uuid4()),
                user_id=user_id,
                request_type="chat_stream",
            )
            set_collector(collector)

        try:
            # Step 1: Get or create conversation (SETUP phase)
            async with track_span("setup"):
                if conversation_id:
                    conversation = await self._get_conversation(user_id, conversation_id)
                    if not conversation:
                        yield {"type": "error", "error": "Conversation not found"}
                        return
                else:
                    conversation = await self._create_conversation(user_id)
                    conversation_id = conversation["id"]

                # Save user message
                user_message = await self._save_message(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    role=MessageRole.USER,
                    content=content,
                )

                # Track conversation and message IDs
                if collector:
                    collector.set_conversation(conversation_id)
                    collector.set_message(user_message["id"])

            # Yield metadata event
            yield {
                "type": "metadata",
                "conversation_id": str(conversation_id),
                "message_id": str(user_message["id"]),
                "user_message_saved": True,
            }

            # Step 2: Analyze query
            async with track_span("query_analysis") as span:
                query_analysis = await self.query_analyzer.analyze(content)

                # Record query analysis metrics
                if collector and span:
                    collector.record_query_analysis(QueryAnalysisMetrics(
                        intent=query_analysis.intent,
                        requires_memory=query_analysis.requires_memory,
                        keywords_count=len(query_analysis.keywords),
                        entities_count=len(query_analysis.entities_mentioned),
                        time_reference=query_analysis.time_reference,
                        memory_types_needed=query_analysis.memory_types_needed or [],
                        confidence=query_analysis.confidence,
                    ))

            # Step 3: Multi-strategy retrieval (if memory enabled)
            memory_context = None
            if include_memory and query_analysis.requires_memory:
                async with track_span("retrieval"):
                    memory_context = await self._retrieve_memories(
                        user_id=user_id,
                        query=content,
                        analysis=query_analysis,
                    )

            # Step 4: Get recent conversation history
            conversation_history = await self._get_conversation_history(
                conversation_id=conversation_id,
                limit=10,  # Last 10 messages for context
            )

            # Step 5: Build prompt context
            async with track_span("context_building"):
                system_prompt = self._build_system_prompt(memory_context)
                messages = self._build_messages(
                    conversation_history=conversation_history,
                    current_message=content,
                    system_prompt=system_prompt,
                )

            # Step 6: Stream LLM response (track TTFB)
            full_response = ""
            first_chunk_received = False
            llm_start_time = time.perf_counter()

            async with track_span("llm_streaming") as llm_span:
                async for chunk in self.llm_client.stream_chat(messages):
                    if chunk.get("type") == "text":
                        # Track time to first byte
                        if not first_chunk_received and llm_span:
                            ttfb_ms = (time.perf_counter() - llm_start_time) * 1000
                            llm_span.metadata["ttfb_ms"] = ttfb_ms
                            first_chunk_received = True

                        full_response += chunk.get("content", "")
                        yield chunk
                    elif chunk.get("type") == "error":
                        if collector:
                            collector.set_error(chunk.get("error", "LLM error"), "llm_error")
                        yield chunk
                        return

                # Record chunk count
                if llm_span:
                    llm_span.metadata["response_length"] = len(full_response)

            # Step 7: Save assistant response
            async with track_span("save_response"):
                assistant_message = await self._save_message(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    role=MessageRole.ASSISTANT,
                    content=full_response,
                )

                # Update conversation
                await self._update_conversation_metadata(
                    conversation_id=conversation_id,
                    message_count_increment=2,
                )

            # Step 8: Enqueue memory extraction task (async, non-blocking)
            async with track_span("enqueue_tasks"):
                await self._enqueue_memory_extraction(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    user_message_id=user_message["id"],
                    assistant_message_id=assistant_message["id"],
                )

            # Log performance
            elapsed = time.time() - start_time
            logger.info(f"Chat completed in {elapsed:.2f}s for user {user_id}")

        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            if collector:
                collector.set_error(str(e), type(e).__name__)
            yield {"type": "error", "error": str(e)}

        finally:
            # Emit analytics (non-blocking)
            if collector:
                analytics = collector.finalize()
                asyncio.create_task(emit_analytics(analytics))
                set_collector(None)  # Clean up context

    async def complete(
        self,
        user_id: str,
        messages: list[dict[str, str]],
        conversation_id: UUID | None = None,
        include_memory: bool = True,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> ChatCompletionResponse:
        """Non-streaming chat completion.

        Args:
            user_id: Current user ID
            messages: List of messages in OpenAI format
            conversation_id: Optional conversation ID
            include_memory: Whether to include memory context
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            ChatCompletionResponse with complete message
        """
        start_time = time.time()

        # Get the last user message
        user_content = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_content = msg.get("content", "")
                break

        # Get or create conversation
        if conversation_id:
            conversation = await self._get_conversation(user_id, conversation_id)
        else:
            conversation = await self._create_conversation(user_id)
            conversation_id = conversation["id"]

        # Save user message
        user_message = await self._save_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=MessageRole.USER,
            content=user_content,
        )

        # Analyze and retrieve memories
        memory_context = None
        if include_memory:
            query_analysis = await self.query_analyzer.analyze(user_content)
            if query_analysis.requires_memory:
                memory_context = await self._retrieve_memories(
                    user_id=user_id,
                    query=user_content,
                    analysis=query_analysis,
                )

        # Build messages with context
        system_prompt = self._build_system_prompt(memory_context)
        formatted_messages = [{"role": "system", "content": system_prompt}]
        formatted_messages.extend(messages)

        # Generate response
        response_content = await self.llm_client.complete(
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Save assistant message
        assistant_message = await self._save_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=MessageRole.ASSISTANT,
            content=response_content,
        )

        # Update conversation
        await self._update_conversation_metadata(
            conversation_id=conversation_id,
            message_count_increment=2,
        )

        # Enqueue memory extraction
        await self._enqueue_memory_extraction(
            user_id=user_id,
            conversation_id=conversation_id,
            user_message_id=user_message["id"],
            assistant_message_id=assistant_message["id"],
        )

        elapsed = time.time() - start_time

        return ChatCompletionResponse(
            id=uuid4(),
            conversation_id=conversation_id,
            message=MessageResponse(
                id=assistant_message["id"],
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=response_content,
                created_at=datetime.utcnow(),
            ),
            usage={
                "completion_time_ms": int(elapsed * 1000),
            },
            memory_context_used=memory_context is not None,
        )

    async def _retrieve_memories(
        self,
        user_id: str,
        query: str,
        analysis: QueryAnalysis,
    ) -> MemoryContext | None:
        """Run multi-strategy retrieval in parallel.

        Args:
            user_id: User ID for isolation
            query: Search query
            analysis: Query analysis results

        Returns:
            MemoryContext with relevant memories
        """
        try:
            # Run parallel retrieval strategies
            results = await self.retrieval_service.multi_strategy_retrieve(
                user_id=user_id,
                query=query,
                analysis=analysis,
            )

            if not results:
                return None

            # Apply hybrid ranking
            ranked_results = self.hybrid_ranker.rank(results)

            # Build context within token budget
            memory_context = await self.context_builder.build(
                memories=ranked_results,
                max_tokens=settings.max_context_tokens,
            )

            return memory_context

        except Exception as e:
            logger.error(f"Memory retrieval error: {e}")
            return None

    def _build_system_prompt(self, memory_context: MemoryContext | None) -> str:
        """Build system prompt with memory context.

        Args:
            memory_context: Optional memory context to include

        Returns:
            Complete system prompt
        """
        base_prompt = """You are a helpful AI assistant with memory capabilities.
You have access to the user's personal context and memories from past interactions.
Use this information naturally in conversation without explicitly mentioning that you're using memory.
Be conversational, helpful, and personalized based on what you know about the user."""

        if memory_context:
            context_str = memory_context.to_prompt_context()
            if context_str:
                base_prompt += f"\n\n# User Context\n{context_str}"

        return base_prompt

    def _build_messages(
        self,
        conversation_history: list[dict],
        current_message: str,
        system_prompt: str,
    ) -> list[dict[str, str]]:
        """Build messages list for LLM.

        Args:
            conversation_history: Recent conversation messages
            current_message: Current user message
            system_prompt: System prompt with context

        Returns:
            Formatted messages list
        """
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for msg in conversation_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # Add current message
        messages.append({"role": "user", "content": current_message})

        return messages

    async def _get_conversation(self, user_id: str, conversation_id: UUID) -> dict | None:
        """Get conversation by ID with user isolation."""
        try:
            response = (
                self.supabase.table("conversations")
                .select("*")
                .eq("id", str(conversation_id))
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Get conversation error: {e}")
            return None

    async def _create_conversation(self, user_id: str, title: str | None = None) -> dict:
        """Create a new conversation."""
        conversation_data = {
            "id": str(uuid4()),
            "user_id": user_id,
            "title": title,
            "message_count": 0,
            "is_active": True,
            "is_archived": False,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = self.supabase.table("conversations").insert(conversation_data).execute()
        return response.data[0] if response.data else conversation_data

    async def _save_message(
        self,
        conversation_id: UUID,
        user_id: str,
        role: MessageRole,
        content: str,
    ) -> dict:
        """Save a message to Supabase."""
        message_data = {
            "id": str(uuid4()),
            "conversation_id": str(conversation_id),
            "user_id": user_id,
            "role": role.value,
            "content": content,
            "created_at": datetime.utcnow().isoformat(),
        }

        response = self.supabase.table("messages").insert(message_data).execute()
        return response.data[0] if response.data else message_data

    async def _get_conversation_history(
        self,
        conversation_id: UUID,
        limit: int = 10,
    ) -> list[dict]:
        """Get recent messages from conversation."""
        try:
            response = (
                self.supabase.table("messages")
                .select("*")
                .eq("conversation_id", str(conversation_id))
                .order("created_at", desc=False)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Get conversation history error: {e}")
            return []

    async def _update_conversation_metadata(
        self,
        conversation_id: UUID,
        message_count_increment: int = 0,
    ) -> None:
        """Update conversation metadata."""
        try:
            # Get current count
            conv = await self._get_conversation_by_id(conversation_id)
            if not conv:
                return

            current_count = conv.get("message_count", 0)

            self.supabase.table("conversations").update({
                "message_count": current_count + message_count_increment,
                "last_message_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", str(conversation_id)).execute()

        except Exception as e:
            logger.error(f"Update conversation metadata error: {e}")

    async def _get_conversation_by_id(self, conversation_id: UUID) -> dict | None:
        """Get conversation without user check."""
        try:
            response = (
                self.supabase.table("conversations")
                .select("*")
                .eq("id", str(conversation_id))
                .single()
                .execute()
            )
            return response.data
        except Exception:
            return None

    async def _enqueue_memory_extraction(
        self,
        user_id: str,
        conversation_id: UUID,
        user_message_id: str,
        assistant_message_id: str,
    ) -> None:
        """Enqueue ARQ task for memory extraction.

        This is non-blocking and runs in the background.
        Uses proper ARQ job format to enqueue extract_entities tasks.
        """
        from arq import create_pool
        from arq.connections import RedisSettings

        try:
            # Get Redis settings from config
            redis_url = settings.redis_url

            # Parse Redis URL
            from urllib.parse import urlparse
            parsed = urlparse(redis_url)

            redis_settings = RedisSettings(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                password=parsed.password,
                database=int(parsed.path.lstrip("/") or 0),
            )

            # Create ARQ Redis pool
            arq_pool = await create_pool(redis_settings)

            try:
                # Enqueue extraction job for user message
                await arq_pool.enqueue_job(
                    "extract_entities",
                    user_message_id,
                    None,  # context
                    _queue_name="jyntrix:queue",
                )

                # Enqueue extraction job for assistant message
                await arq_pool.enqueue_job(
                    "extract_entities",
                    assistant_message_id,
                    None,  # context
                    _queue_name="jyntrix:queue",
                )

                logger.info(
                    f"Memory extraction tasks enqueued for conversation {conversation_id}: "
                    f"user_msg={user_message_id}, assistant_msg={assistant_message_id}"
                )
            finally:
                await arq_pool.close()

        except Exception as e:
            logger.error(f"Failed to enqueue memory extraction: {e}")
            # Don't raise - this is non-critical

    # Public API methods for router

    async def create_conversation(
        self,
        user_id: str,
        title: str | None = None,
        metadata: dict | None = None,
        initial_message: str | None = None,
    ) -> ConversationResponse:
        """Create a new conversation."""
        conversation = await self._create_conversation(user_id, title)

        if initial_message:
            # If initial message provided, process it
            async for _ in self.send_message_stream(
                user_id=user_id,
                content=initial_message,
                conversation_id=UUID(conversation["id"]),
            ):
                pass  # Consume the generator

        return ConversationResponse(
            id=UUID(conversation["id"]),
            user_id=user_id,
            title=title,
            message_count=2 if initial_message else 0,
            is_active=True,
            is_archived=False,
            created_at=datetime.fromisoformat(conversation["created_at"]),
            updated_at=datetime.fromisoformat(conversation["updated_at"]),
        )

    async def list_conversations(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        archived: bool = False,
    ) -> ConversationListResponse:
        """List user's conversations."""
        offset = (page - 1) * page_size

        # Get conversations
        response = (
            self.supabase.table("conversations")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .eq("is_archived", archived)
            .order("updated_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

        conversations = []
        for conv in response.data or []:
            conversations.append(ConversationResponse(
                id=UUID(conv["id"]),
                user_id=conv["user_id"],
                title=conv.get("title"),
                summary=conv.get("summary"),
                message_count=conv.get("message_count", 0),
                total_tokens=conv.get("total_tokens", 0),
                is_active=conv.get("is_active", True),
                is_archived=conv.get("is_archived", False),
                created_at=datetime.fromisoformat(conv["created_at"]),
                updated_at=datetime.fromisoformat(conv["updated_at"]),
                last_message_at=datetime.fromisoformat(conv["last_message_at"])
                    if conv.get("last_message_at") else None,
            ))

        total = response.count or len(conversations)

        return ConversationListResponse(
            conversations=conversations,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )

    async def get_conversation(
        self,
        user_id: str,
        conversation_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> ConversationDetailResponse | None:
        """Get conversation with messages."""
        conv = await self._get_conversation(user_id, conversation_id)
        if not conv:
            return None

        # Get messages
        messages_response = (
            self.supabase.table("messages")
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("created_at", desc=False)
            .range(offset, offset + limit - 1)
            .execute()
        )

        messages = []
        for msg in messages_response.data or []:
            messages.append(MessageResponse(
                id=UUID(msg["id"]),
                conversation_id=UUID(msg["conversation_id"]),
                role=MessageRole(msg["role"]),
                content=msg["content"],
                tokens=msg.get("tokens"),
                created_at=datetime.fromisoformat(msg["created_at"]),
            ))

        return ConversationDetailResponse(
            id=UUID(conv["id"]),
            user_id=conv["user_id"],
            title=conv.get("title"),
            summary=conv.get("summary"),
            message_count=conv.get("message_count", 0),
            total_tokens=conv.get("total_tokens", 0),
            is_active=conv.get("is_active", True),
            is_archived=conv.get("is_archived", False),
            created_at=datetime.fromisoformat(conv["created_at"]),
            updated_at=datetime.fromisoformat(conv["updated_at"]),
            last_message_at=datetime.fromisoformat(conv["last_message_at"])
                if conv.get("last_message_at") else None,
            messages=messages,
        )

    async def update_conversation(
        self,
        user_id: str,
        conversation_id: UUID,
        title: str | None = None,
        is_archived: bool | None = None,
        metadata: dict | None = None,
    ) -> ConversationResponse | None:
        """Update a conversation."""
        # Verify ownership
        conv = await self._get_conversation(user_id, conversation_id)
        if not conv:
            return None

        update_data = {"updated_at": datetime.utcnow().isoformat()}
        if title is not None:
            update_data["title"] = title
        if is_archived is not None:
            update_data["is_archived"] = is_archived
        if metadata is not None:
            update_data["metadata"] = metadata

        response = (
            self.supabase.table("conversations")
            .update(update_data)
            .eq("id", str(conversation_id))
            .execute()
        )

        updated = response.data[0] if response.data else conv

        return ConversationResponse(
            id=UUID(updated["id"]),
            user_id=updated["user_id"],
            title=updated.get("title"),
            summary=updated.get("summary"),
            message_count=updated.get("message_count", 0),
            total_tokens=updated.get("total_tokens", 0),
            is_active=updated.get("is_active", True),
            is_archived=updated.get("is_archived", False),
            created_at=datetime.fromisoformat(updated["created_at"]),
            updated_at=datetime.fromisoformat(updated["updated_at"]),
        )

    async def delete_conversation(
        self,
        user_id: str,
        conversation_id: UUID,
    ) -> bool:
        """Delete a conversation and its messages."""
        # Verify ownership
        conv = await self._get_conversation(user_id, conversation_id)
        if not conv:
            return False

        # Delete messages first
        self.supabase.table("messages").delete().eq(
            "conversation_id", str(conversation_id)
        ).execute()

        # Delete conversation
        self.supabase.table("conversations").delete().eq(
            "id", str(conversation_id)
        ).execute()

        return True

    async def get_messages(
        self,
        user_id: str,
        conversation_id: UUID,
        limit: int = 50,
        offset: int = 0,
        order: str = "asc",
    ) -> list[MessageResponse]:
        """Get messages from a conversation."""
        # Verify ownership
        conv = await self._get_conversation(user_id, conversation_id)
        if not conv:
            return []

        response = (
            self.supabase.table("messages")
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("created_at", desc=(order == "desc"))
            .range(offset, offset + limit - 1)
            .execute()
        )

        messages = []
        for msg in response.data or []:
            messages.append(MessageResponse(
                id=UUID(msg["id"]),
                conversation_id=UUID(msg["conversation_id"]),
                role=MessageRole(msg["role"]),
                content=msg["content"],
                tokens=msg.get("tokens"),
                created_at=datetime.fromisoformat(msg["created_at"]),
            ))

        return messages
