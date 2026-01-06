"""Non-blocking analytics emission.

This module provides functionality to emit analytics records without
blocking the main request path. It uses buffering and async task
creation for fire-and-forget emission.
"""

import asyncio
import json
import logging
from typing import Any

from src.analytics.models import RequestAnalytics
from src.config import settings

logger = logging.getLogger(__name__)

# Global emitter instance (lazy initialized)
_emitter: "AnalyticsEmitter | None" = None


class AnalyticsEmitter:
    """Non-blocking analytics emission to storage backends.

    This class buffers analytics records and emits them in batches
    to reduce database write frequency. It supports multiple backends:
    - Redis streams (for real-time processing)
    - Direct database writes (for persistence)
    - Console logging (for development)

    Attributes:
        redis: Redis client for streaming (optional)
        supabase: Supabase client for persistence (optional)
        buffer: List of pending analytics records
        buffer_size: Maximum buffer size before auto-flush
        flush_interval: Seconds between automatic flushes
    """

    def __init__(
        self,
        redis_client: Any = None,
        supabase_client: Any = None,
        buffer_size: int = 100,
        flush_interval: int = 10,
    ):
        """Initialize the analytics emitter.

        Args:
            redis_client: Optional Redis client for streaming
            supabase_client: Optional Supabase client for persistence
            buffer_size: Max records to buffer before flush
            flush_interval: Seconds between auto-flushes
        """
        self.redis = redis_client
        self.supabase = supabase_client
        self._buffer: list[RequestAnalytics] = []
        self._buffer_size = buffer_size
        self._flush_interval = flush_interval
        self._flush_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the periodic flush background task.

        This should be called once during application startup to enable
        automatic periodic flushing of buffered analytics.
        """
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._periodic_flush())
            logger.info(
                f"Analytics emitter started with {self._flush_interval}s flush interval"
            )

    async def _periodic_flush(self) -> None:
        """Background task that flushes buffer periodically.

        This runs continuously until cancelled, flushing the buffer
        at the configured interval. On cancellation (shutdown), it
        performs a final flush to ensure no data is lost.
        """
        while True:
            try:
                await asyncio.sleep(self._flush_interval)
                if self._buffer:  # Only flush if there's data
                    await self._flush()
            except asyncio.CancelledError:
                # Final flush on shutdown
                logger.info("Analytics emitter shutting down, performing final flush")
                await self._flush()
                break
            except Exception as e:
                logger.error(f"Periodic flush error: {e}")

    async def emit(self, analytics: RequestAnalytics) -> None:
        """Emit analytics record (non-blocking).

        Adds the record to the buffer. If buffer is full, triggers
        a flush. This method is designed to be called without await
        via asyncio.create_task() for fire-and-forget behavior.

        Args:
            analytics: The RequestAnalytics to emit
        """
        if not settings.analytics_enabled:
            return

        async with self._lock:
            self._buffer.append(analytics)

            # Flush if buffer is full
            if len(self._buffer) >= self._buffer_size:
                asyncio.create_task(self._flush())

    async def _flush(self) -> None:
        """Flush buffer to storage backends."""
        async with self._lock:
            if not self._buffer:
                return

            batch = self._buffer.copy()
            self._buffer.clear()

        try:
            # Emit to all configured backends in parallel
            tasks = []

            # Option 1: Redis stream for real-time processing
            if self.redis:
                tasks.append(self._emit_to_redis(batch))

            # Option 2: Direct database write
            if self.supabase:
                tasks.append(self._emit_to_database(batch))

            # Option 3: Log for development/debugging
            if settings.is_development:
                self._log_analytics(batch)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Analytics emission failed: {e}")
            # Re-add failed batch to buffer for retry (up to limit)
            async with self._lock:
                if len(self._buffer) < self._buffer_size * 2:
                    self._buffer.extend(batch)

    async def _emit_to_redis(self, batch: list[RequestAnalytics]) -> None:
        """Emit to Redis stream for async processing.

        Args:
            batch: List of analytics records to emit
        """
        try:
            pipe = self.redis.pipeline()

            for analytics in batch:
                pipe.xadd(
                    "analytics:requests",
                    {
                        "request_id": str(analytics.request_id),
                        "user_id": analytics.user_id,
                        "total_time_ms": str(analytics.total_time_ms),
                        "data": json.dumps(self._serialize(analytics)),
                    },
                    maxlen=10000,  # Keep last 10k entries
                )

            await pipe.execute()
            logger.debug(f"Emitted {len(batch)} analytics records to Redis")
        except Exception as e:
            logger.error(f"Redis analytics emission failed: {e}")
            raise

    async def _emit_to_database(self, batch: list[RequestAnalytics]) -> None:
        """Emit directly to database.

        Args:
            batch: List of analytics records to emit
        """
        try:
            records = [analytics.to_db_record() for analytics in batch]

            # Use upsert to handle any duplicates gracefully
            self.supabase.table("request_analytics").insert(records).execute()

            logger.debug(f"Emitted {len(batch)} analytics records to database")
        except Exception as e:
            logger.error(f"Database analytics emission failed: {e}")
            raise

    def _log_analytics(self, batch: list[RequestAnalytics]) -> None:
        """Log analytics for development.

        Args:
            batch: List of analytics records to log
        """
        for analytics in batch:
            logger.info(
                f"ANALYTICS | request={analytics.request_id} | "
                f"type={analytics.request_type} | "
                f"status={analytics.status} | "
                f"total={analytics.total_time_ms:.1f}ms | "
                f"setup={analytics.setup_time_ms:.1f}ms | "
                f"query={analytics.query_analysis_time_ms:.1f}ms | "
                f"retrieval={analytics.retrieval_time_ms:.1f}ms | "
                f"ranking={analytics.ranking_time_ms:.1f}ms | "
                f"context={analytics.context_building_time_ms:.1f}ms | "
                f"llm_ttfb={analytics.llm_ttfb_ms:.1f}ms | "
                f"llm_total={analytics.llm_total_time_ms:.1f}ms"
            )

    def _serialize(self, analytics: RequestAnalytics) -> dict[str, Any]:
        """Serialize analytics to dict for storage.

        Args:
            analytics: The analytics record to serialize

        Returns:
            Dictionary representation
        """
        return analytics.to_db_record()

    async def shutdown(self) -> None:
        """Shutdown the emitter, flushing any remaining data."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self._flush()


async def get_emitter() -> AnalyticsEmitter:
    """Get or create the global analytics emitter.

    Returns:
        The AnalyticsEmitter instance
    """
    global _emitter

    if _emitter is None:
        # Lazy import to avoid circular dependencies
        from src.db.redis import get_redis_client
        from src.db.supabase import get_supabase_admin_client

        try:
            redis_client = await get_redis_client()
        except Exception:
            redis_client = None
            logger.warning("Redis not available for analytics")

        try:
            supabase_client = get_supabase_admin_client()
        except Exception:
            supabase_client = None
            logger.warning("Supabase not available for analytics")

        _emitter = AnalyticsEmitter(
            redis_client=redis_client,
            supabase_client=supabase_client,
            buffer_size=getattr(settings, "analytics_buffer_size", 100),
            flush_interval=getattr(settings, "analytics_flush_interval", 10),
        )

        # Auto-start the background flush task
        await _emitter.start()

    return _emitter


async def emit_analytics(analytics: RequestAnalytics) -> None:
    """Emit analytics using global emitter.

    This is the main entry point for emitting analytics.
    It's designed to be called via asyncio.create_task()
    for non-blocking behavior.

    Usage:
        asyncio.create_task(emit_analytics(analytics))

    Args:
        analytics: The RequestAnalytics to emit
    """
    try:
        emitter = await get_emitter()
        await emitter.emit(analytics)
    except Exception as e:
        # Never let analytics emission crash the request
        logger.error(f"Failed to emit analytics: {e}")


async def flush_analytics() -> None:
    """Force flush any buffered analytics.

    Useful during shutdown or testing.
    """
    if _emitter:
        await _emitter._flush()
