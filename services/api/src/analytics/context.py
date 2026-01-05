"""Request-scoped analytics context using ContextVar.

This module provides a thread-safe, async-safe way to propagate
analytics collection through the request lifecycle using Python's
contextvars.
"""

import time
from contextvars import ContextVar
from typing import Any
from uuid import UUID, uuid4

from src.analytics.models import (
    ContextMetrics,
    LLMMetrics,
    QueryAnalysisMetrics,
    RequestAnalytics,
    RetrievalMetrics,
    SpanStatus,
    TimingSpan,
)

# Context variable for request-scoped analytics
_analytics_context: ContextVar[Any] = ContextVar(
    "analytics_context",
    default=None,
)


class AnalyticsCollector:
    """Request-scoped analytics collector with hierarchical span tracking.

    This class manages the collection of timing spans and metrics
    throughout a request's lifecycle. It uses a stack-based approach
    for hierarchical span management.

    Usage:
        collector = AnalyticsCollector(request_id, user_id)
        set_collector(collector)

        with track_span("operation"):
            # do work

        analytics = collector.finalize()
    """

    def __init__(
        self,
        request_id: str | UUID | None = None,
        user_id: str = "",
        request_type: str = "chat_stream",
    ):
        """Initialize the analytics collector.

        Args:
            request_id: Unique request identifier (generated if not provided)
            user_id: User ID for the request
            request_type: Type of request (chat_stream, chat_complete, etc.)
        """
        self.analytics = RequestAnalytics(
            request_id=UUID(str(request_id)) if request_id else uuid4(),
            user_id=user_id,
            request_type=request_type,
        )
        self._span_stack: list[TimingSpan] = []
        self._request_start = time.perf_counter()

    def start_span(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> TimingSpan:
        """Start a new timing span.

        Args:
            name: Name of the span (e.g., "query_analysis", "vector_search")
            metadata: Optional initial metadata for the span

        Returns:
            The created TimingSpan
        """
        span = TimingSpan(
            name=name,
            start_time=time.perf_counter(),
            status=SpanStatus.RUNNING,
            metadata=metadata or {},
        )

        # Attach to parent span if exists, otherwise set as root
        if self._span_stack:
            self._span_stack[-1].children.append(span)
        elif self.analytics.root_span is None:
            self.analytics.root_span = span

        self._span_stack.append(span)
        return span

    def end_span(
        self,
        metadata: dict[str, Any] | None = None,
    ) -> TimingSpan | None:
        """End the current span.

        Args:
            metadata: Optional metadata to add on completion

        Returns:
            The completed TimingSpan, or None if no span was active
        """
        if not self._span_stack:
            return None

        span = self._span_stack.pop()
        span.complete(time.perf_counter(), metadata)

        # Update flat timing fields for quick access
        self._update_phase_timing(span)

        return span

    def fail_span(self, error: str) -> TimingSpan | None:
        """Mark current span as failed.

        Args:
            error: Error message describing the failure

        Returns:
            The failed TimingSpan, or None if no span was active
        """
        if not self._span_stack:
            return None

        span = self._span_stack.pop()
        span.fail(time.perf_counter(), error)
        self._update_phase_timing(span)

        # Update overall status if this is a critical failure
        if span.name in ("llm_streaming", "retrieval"):
            self.analytics.status = "error"
            self.analytics.error_message = error
            self.analytics.error_type = span.name + "_error"

        return span

    def record_retrieval(self, metrics: RetrievalMetrics) -> None:
        """Record retrieval strategy metrics.

        Args:
            metrics: RetrievalMetrics for a specific strategy
        """
        self.analytics.retrieval_metrics.append(metrics)

        # Update strategy-specific timing
        if metrics.duration_ms:
            if metrics.strategy == "vector":
                self.analytics.vector_search_time_ms = metrics.duration_ms
            elif metrics.strategy == "keyword":
                self.analytics.keyword_search_time_ms = metrics.duration_ms
            elif metrics.strategy == "graph":
                self.analytics.graph_search_time_ms = metrics.duration_ms
            elif metrics.strategy == "profile":
                self.analytics.profile_retrieval_time_ms = metrics.duration_ms
            elif metrics.strategy == "recent":
                self.analytics.recent_context_time_ms = metrics.duration_ms

    def record_context(self, metrics: ContextMetrics) -> None:
        """Record context building metrics.

        Args:
            metrics: ContextMetrics from context builder
        """
        self.analytics.context_metrics = metrics

    def record_llm(self, metrics: LLMMetrics) -> None:
        """Record LLM metrics.

        Args:
            metrics: LLMMetrics from LLM client
        """
        self.analytics.llm_metrics = metrics
        if metrics.time_to_first_byte_ms:
            self.analytics.llm_ttfb_ms = metrics.time_to_first_byte_ms
        if metrics.total_generation_time_ms:
            self.analytics.llm_total_time_ms = metrics.total_generation_time_ms

    def record_query_analysis(self, metrics: QueryAnalysisMetrics) -> None:
        """Record query analysis metrics.

        Args:
            metrics: QueryAnalysisMetrics from query analyzer
        """
        self.analytics.query_analysis_metrics = metrics

    def set_conversation(self, conversation_id: UUID | str) -> None:
        """Set the conversation ID.

        Args:
            conversation_id: The conversation UUID
        """
        self.analytics.conversation_id = (
            UUID(str(conversation_id)) if isinstance(conversation_id, str) else conversation_id
        )

    def set_message(self, message_id: UUID | str) -> None:
        """Set the message ID.

        Args:
            message_id: The message UUID
        """
        self.analytics.message_id = (
            UUID(str(message_id)) if isinstance(message_id, str) else message_id
        )

    def set_error(self, error_message: str, error_type: str | None = None) -> None:
        """Set error information.

        Args:
            error_message: Description of the error
            error_type: Category of error (optional)
        """
        self.analytics.status = "error"
        self.analytics.error_message = error_message
        self.analytics.error_type = error_type

    def _update_phase_timing(self, span: TimingSpan) -> None:
        """Map span names to flat timing fields.

        Args:
            span: The completed TimingSpan
        """
        if span.duration_ms is None:
            return

        mapping = {
            "setup": "setup_time_ms",
            "query_analysis": "query_analysis_time_ms",
            "retrieval": "retrieval_time_ms",
            "parallel_retrieval": "retrieval_time_ms",
            "ranking": "ranking_time_ms",
            "hybrid_ranking": "ranking_time_ms",
            "context_building": "context_building_time_ms",
            "llm_streaming": "llm_total_time_ms",
            "save_response": "save_time_ms",
            "enqueue_tasks": "enqueue_time_ms",
            # Individual retrieval strategies
            "vector_search": "vector_search_time_ms",
            "keyword_search": "keyword_search_time_ms",
            "graph_search": "graph_search_time_ms",
            "profile_retrieval": "profile_retrieval_time_ms",
            "recent_context": "recent_context_time_ms",
        }

        if span.name in mapping:
            setattr(self.analytics, mapping[span.name], span.duration_ms)

        # Extract TTFB from llm_streaming metadata
        if span.name == "llm_streaming" and "ttfb_ms" in span.metadata:
            self.analytics.llm_ttfb_ms = span.metadata["ttfb_ms"]

    def finalize(self) -> RequestAnalytics:
        """Finalize and return analytics.

        This should be called after request processing is complete.
        It calculates total time and closes any open spans.

        Returns:
            The completed RequestAnalytics
        """
        # Close any remaining open spans
        while self._span_stack:
            self.end_span({"auto_closed": True})

        # Calculate total time
        self.analytics.total_time_ms = (time.perf_counter() - self._request_start) * 1000

        return self.analytics


def get_collector() -> AnalyticsCollector | None:
    """Get current request's analytics collector.

    Returns:
        The AnalyticsCollector for the current context, or None if not set
    """
    return _analytics_context.get()


def set_collector(collector: AnalyticsCollector | None) -> None:
    """Set analytics collector for current request context.

    Args:
        collector: The AnalyticsCollector to set, or None to clear
    """
    _analytics_context.set(collector)
