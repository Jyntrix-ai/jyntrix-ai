"""Analytics module for request tracking and performance metrics.

This module provides:
- RequestAnalytics: Data structures for analytics collection
- AnalyticsCollector: Request-scoped collector using ContextVar
- track_span: Zero-overhead context manager for timing spans
- emit_analytics: Non-blocking analytics emission
"""

from src.analytics.context import (
    AnalyticsCollector,
    get_collector,
    set_collector,
)
from src.analytics.emitter import emit_analytics
from src.analytics.instrumentation import (
    ParallelSpanTracker,
    timed_async,
    timed_sync,
    track_span,
    track_span_sync,
)
from src.analytics.models import (
    ContextMetrics,
    LLMMetrics,
    QueryAnalysisMetrics,
    RequestAnalytics,
    RetrievalMetrics,
    SpanStatus,
    TimingSpan,
)

__all__ = [
    # Models
    "TimingSpan",
    "SpanStatus",
    "RetrievalMetrics",
    "ContextMetrics",
    "LLMMetrics",
    "QueryAnalysisMetrics",
    "RequestAnalytics",
    # Context
    "AnalyticsCollector",
    "get_collector",
    "set_collector",
    # Instrumentation
    "track_span",
    "track_span_sync",
    "timed_async",
    "timed_sync",
    "ParallelSpanTracker",
    # Emitter
    "emit_analytics",
]
