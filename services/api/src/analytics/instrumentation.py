"""Zero-overhead instrumentation helpers.

This module provides decorators and context managers for timing spans
that have minimal overhead when analytics is disabled.
"""

import functools
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Callable, Generator, ParamSpec, TypeVar

from src.analytics.context import AnalyticsCollector, get_collector
from src.analytics.models import RetrievalMetrics, SpanStatus, TimingSpan

P = ParamSpec("P")
T = TypeVar("T")


@asynccontextmanager
async def track_span(
    name: str,
    metadata: dict[str, Any] | None = None,
) -> AsyncGenerator[TimingSpan | None, None]:
    """Async context manager for timing spans.

    Zero overhead if analytics not enabled (collector is None).

    Usage:
        async with track_span("query_analysis"):
            result = await analyzer.analyze(query)

        # With metadata access:
        async with track_span("llm_streaming") as span:
            # do work
            if span:
                span.metadata["ttfb_ms"] = ttfb

    Args:
        name: Name of the span
        metadata: Optional initial metadata

    Yields:
        The TimingSpan if collector exists, None otherwise
    """
    collector = get_collector()

    if collector is None:
        # No analytics context - zero overhead path
        yield None
        return

    span = collector.start_span(name, metadata)
    try:
        yield span
    except Exception as e:
        collector.fail_span(str(e))
        raise
    else:
        collector.end_span()


@contextmanager
def track_span_sync(
    name: str,
    metadata: dict[str, Any] | None = None,
) -> Generator[TimingSpan | None, None, None]:
    """Sync context manager for timing spans.

    Zero overhead if analytics not enabled (collector is None).

    Usage:
        with track_span_sync("ranking"):
            result = ranker.rank(items)

    Args:
        name: Name of the span
        metadata: Optional initial metadata

    Yields:
        The TimingSpan if collector exists, None otherwise
    """
    collector = get_collector()

    if collector is None:
        yield None
        return

    span = collector.start_span(name, metadata)
    try:
        yield span
    except Exception as e:
        collector.fail_span(str(e))
        raise
    else:
        collector.end_span()


def timed_async(span_name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for async functions to add timing spans.

    Usage:
        @timed_async("vector_search")
        async def search(self, user_id: str, query: str) -> list[dict]:
            ...

    Args:
        span_name: Name for the timing span

    Returns:
        Decorated function
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            async with track_span(span_name):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def timed_sync(span_name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for sync functions to add timing spans.

    Usage:
        @timed_sync("ranking")
        def rank(self, items: list) -> list:
            ...

    Args:
        span_name: Name for the timing span

    Returns:
        Decorated function
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            with track_span_sync(span_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator


class ParallelSpanTracker:
    """Track multiple parallel operations (like asyncio.gather).

    This class helps track timing for multiple concurrent operations
    that are run in parallel (e.g., via asyncio.gather).

    Usage:
        tracker = ParallelSpanTracker("retrieval")
        results = await asyncio.gather(
            tracker.track("vector", vector_search()),
            tracker.track("keyword", keyword_search()),
            return_exceptions=True
        )
        tracker.finalize()

    Attributes:
        parent_name: Name of the parent span
        collector: Analytics collector (may be None)
        spans: Dictionary of child span names to TimingSpans
        start_time: Start time of parallel operation
    """

    def __init__(self, parent_name: str):
        """Initialize parallel span tracker.

        Args:
            parent_name: Name for the parent span encompassing all parallel ops
        """
        self.parent_name = parent_name
        self.collector = get_collector()
        self.spans: dict[str, TimingSpan] = {}
        self.start_time = time.perf_counter()
        self.parent_span: TimingSpan | None = None

        if self.collector:
            self.parent_span = self.collector.start_span(parent_name)

    async def track(self, name: str, coro: Any) -> Any:
        """Wrap a coroutine with timing.

        Args:
            name: Name for this specific operation
            coro: The coroutine to track

        Returns:
            Result of the coroutine
        """
        if not self.collector:
            return await coro

        start = time.perf_counter()
        try:
            result = await coro
            duration = (time.perf_counter() - start) * 1000

            span = TimingSpan(
                name=name,
                start_time=start,
                duration_ms=duration,
                status=SpanStatus.COMPLETED,
            )
            span.end_time = time.perf_counter()
            self.spans[name] = span

            return result
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            span = TimingSpan(
                name=name,
                start_time=start,
                duration_ms=duration,
                status=SpanStatus.FAILED,
                error=str(e),
            )
            span.end_time = time.perf_counter()
            self.spans[name] = span
            raise

    def record_retrieval_metrics(
        self,
        strategy: str,
        results: list[dict[str, Any]],
    ) -> None:
        """Record retrieval metrics for a strategy.

        Args:
            strategy: Name of the retrieval strategy
            results: List of result dictionaries with 'score' fields
        """
        if not self.collector:
            return

        scores = [r.get("score", 0) for r in results if r.get("score") is not None]
        memory_types = [r.get("memory_type", r.get("type", "")) for r in results]

        duration_ms = None
        if strategy in self.spans:
            duration_ms = self.spans[strategy].duration_ms

        metrics = RetrievalMetrics(
            strategy=strategy,
            result_count=len(results),
            score_min=min(scores) if scores else None,
            score_max=max(scores) if scores else None,
            score_avg=sum(scores) / len(scores) if scores else None,
            duration_ms=duration_ms,
            memory_types=memory_types,
        )
        self.collector.record_retrieval(metrics)

    def finalize(self, metadata: dict[str, Any] | None = None) -> None:
        """Finalize parallel tracking and record spans.

        Args:
            metadata: Optional metadata for the parent span
        """
        if not self.collector or not self.parent_span:
            return

        # Add all child spans to parent
        for span in self.spans.values():
            self.parent_span.children.append(span)

        # Add aggregate metadata
        final_metadata = metadata or {}
        final_metadata["child_operations"] = list(self.spans.keys())
        final_metadata["child_timings"] = {
            name: span.duration_ms for name, span in self.spans.items()
        }

        # Find the max duration (parallel execution time = max of children)
        max_duration = max(
            (span.duration_ms or 0 for span in self.spans.values()),
            default=0,
        )
        final_metadata["parallel_max_duration_ms"] = max_duration

        # Complete parent span
        self.collector.end_span(final_metadata)
