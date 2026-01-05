"""Data models for analytics collection.

These dataclasses represent the structured data collected during request processing.
They are designed to be lightweight and serializable for storage.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class SpanStatus(str, Enum):
    """Status of a timing span."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TimingSpan:
    """Individual timing measurement for a single operation.

    Represents a hierarchical timing span that can contain child spans
    for nested operations.
    """

    name: str
    start_time: float  # time.perf_counter() for precision
    end_time: float | None = None
    duration_ms: float | None = None
    status: SpanStatus = SpanStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    children: list["TimingSpan"] = field(default_factory=list)

    def complete(self, end_time: float, metadata: dict[str, Any] | None = None) -> None:
        """Mark span as completed with timing."""
        self.end_time = end_time
        self.duration_ms = (end_time - self.start_time) * 1000
        self.status = SpanStatus.COMPLETED
        if metadata:
            self.metadata.update(metadata)

    def fail(self, end_time: float, error: str) -> None:
        """Mark span as failed with error."""
        self.end_time = end_time
        self.duration_ms = (end_time - self.start_time) * 1000
        self.status = SpanStatus.FAILED
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert span to dictionary for serialization."""
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "metadata": self.metadata,
            "error": self.error,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class RetrievalMetrics:
    """Metrics specific to a single retrieval strategy."""

    strategy: str  # vector, keyword, entity, profile, recent
    result_count: int = 0
    score_min: float | None = None
    score_max: float | None = None
    score_avg: float | None = None
    duration_ms: float | None = None
    memory_types: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "strategy": self.strategy,
            "result_count": self.result_count,
            "score_min": self.score_min,
            "score_max": self.score_max,
            "score_avg": self.score_avg,
            "duration_ms": self.duration_ms,
            "memory_types": self.memory_types,
        }


@dataclass
class ContextMetrics:
    """Metrics for context building."""

    profile_tokens_used: int = 0
    semantic_tokens_used: int = 0
    episodic_tokens_used: int = 0
    procedural_tokens_used: int = 0
    entity_tokens_used: int = 0
    total_context_tokens: int = 0
    token_budget_max: int = 0
    truncation_occurred: bool = False
    memories_included: int = 0
    memories_truncated: int = 0
    memory_count_by_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "profile_tokens_used": self.profile_tokens_used,
            "semantic_tokens_used": self.semantic_tokens_used,
            "episodic_tokens_used": self.episodic_tokens_used,
            "procedural_tokens_used": self.procedural_tokens_used,
            "entity_tokens_used": self.entity_tokens_used,
            "total_context_tokens": self.total_context_tokens,
            "token_budget_max": self.token_budget_max,
            "truncation_occurred": self.truncation_occurred,
            "memories_included": self.memories_included,
            "memories_truncated": self.memories_truncated,
            "memory_count_by_type": self.memory_count_by_type,
        }


@dataclass
class LLMMetrics:
    """Metrics for LLM interaction."""

    time_to_first_byte_ms: float | None = None
    total_generation_time_ms: float | None = None
    chunk_count: int = 0
    output_tokens_estimate: int = 0  # Based on response length
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "time_to_first_byte_ms": self.time_to_first_byte_ms,
            "total_generation_time_ms": self.total_generation_time_ms,
            "chunk_count": self.chunk_count,
            "output_tokens_estimate": self.output_tokens_estimate,
            "model": self.model,
        }


@dataclass
class QueryAnalysisMetrics:
    """Query analysis results for analytics."""

    intent: str = ""
    requires_memory: bool = True
    keywords_count: int = 0
    entities_count: int = 0
    time_reference: str | None = None
    memory_types_needed: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "intent": self.intent,
            "requires_memory": self.requires_memory,
            "keywords_count": self.keywords_count,
            "entities_count": self.entities_count,
            "time_reference": self.time_reference,
            "memory_types_needed": self.memory_types_needed,
            "confidence": self.confidence,
        }


@dataclass
class RequestAnalytics:
    """Complete analytics for a single request.

    This is the main data structure that collects all metrics
    during a request's lifecycle.
    """

    # Identification
    request_id: UUID = field(default_factory=uuid4)
    user_id: str = ""
    conversation_id: UUID | None = None
    message_id: UUID | None = None
    request_type: str = "chat_stream"

    # Timing hierarchy (for detailed tracing)
    root_span: TimingSpan | None = None

    # Phase timings (flat for quick access and querying)
    setup_time_ms: float = 0.0
    query_analysis_time_ms: float = 0.0
    retrieval_time_ms: float = 0.0
    ranking_time_ms: float = 0.0
    context_building_time_ms: float = 0.0
    llm_ttfb_ms: float = 0.0
    llm_total_time_ms: float = 0.0
    save_time_ms: float = 0.0
    enqueue_time_ms: float = 0.0
    total_time_ms: float = 0.0

    # Detailed strategy timings
    vector_search_time_ms: float = 0.0
    keyword_search_time_ms: float = 0.0
    graph_search_time_ms: float = 0.0
    profile_retrieval_time_ms: float = 0.0
    recent_context_time_ms: float = 0.0

    # Detailed metrics
    retrieval_metrics: list[RetrievalMetrics] = field(default_factory=list)
    context_metrics: ContextMetrics | None = None
    llm_metrics: LLMMetrics | None = None
    query_analysis_metrics: QueryAnalysisMetrics | None = None

    # Request metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: str = "success"  # success, partial, error, timeout
    error_message: str | None = None
    error_type: str | None = None

    def get_step_timings(self) -> dict[str, float | None]:
        """Get flat dictionary of step timings."""
        return {
            "setup_time": self.setup_time_ms if self.setup_time_ms else None,
            "query_analysis_time": self.query_analysis_time_ms if self.query_analysis_time_ms else None,
            "vector_search_time": self.vector_search_time_ms if self.vector_search_time_ms else None,
            "keyword_search_time": self.keyword_search_time_ms if self.keyword_search_time_ms else None,
            "graph_search_time": self.graph_search_time_ms if self.graph_search_time_ms else None,
            "profile_retrieval_time": self.profile_retrieval_time_ms if self.profile_retrieval_time_ms else None,
            "recent_context_time": self.recent_context_time_ms if self.recent_context_time_ms else None,
            "total_retrieval_time": self.retrieval_time_ms if self.retrieval_time_ms else None,
            "ranking_time": self.ranking_time_ms if self.ranking_time_ms else None,
            "context_building_time": self.context_building_time_ms if self.context_building_time_ms else None,
            "llm_ttfb": self.llm_ttfb_ms if self.llm_ttfb_ms else None,
            "llm_total_time": self.llm_total_time_ms if self.llm_total_time_ms else None,
            "save_response_time": self.save_time_ms if self.save_time_ms else None,
        }

    def get_retrieval_metrics_dict(self) -> dict[str, Any]:
        """Get aggregated retrieval metrics as dictionary."""
        if not self.retrieval_metrics:
            return {}

        # Aggregate by strategy
        vector_count = keyword_count = graph_count = profile_count = recent_count = 0
        total_raw = 0
        scores: dict[str, list[float]] = {"vector": [], "keyword": [], "combined": []}
        memory_types: dict[str, int] = {}

        for m in self.retrieval_metrics:
            total_raw += m.result_count
            if m.strategy == "vector":
                vector_count = m.result_count
                if m.score_avg is not None:
                    scores["vector"].append(m.score_avg)
            elif m.strategy == "keyword":
                keyword_count = m.result_count
                if m.score_avg is not None:
                    scores["keyword"].append(m.score_avg)
            elif m.strategy == "graph":
                graph_count = m.result_count
            elif m.strategy == "profile":
                profile_count = m.result_count
            elif m.strategy == "recent":
                recent_count = m.result_count

            # Count memory types
            for mt in m.memory_types:
                memory_types[mt] = memory_types.get(mt, 0) + 1

        # Calculate score distributions
        score_dist = {}
        for strategy, score_list in scores.items():
            if score_list:
                score_dist[strategy] = {
                    "min": min(score_list),
                    "max": max(score_list),
                    "avg": sum(score_list) / len(score_list),
                }

        return {
            "vector_results_count": vector_count,
            "keyword_results_count": keyword_count,
            "graph_results_count": graph_count,
            "profile_results_count": profile_count,
            "recent_results_count": recent_count,
            "total_raw_results": total_raw,
            "score_distribution": score_dist,
            "memories_by_type": memory_types,
        }

    def to_db_record(self) -> dict[str, Any]:
        """Convert to database record format."""
        return {
            "user_id": self.user_id,
            "conversation_id": str(self.conversation_id) if self.conversation_id else None,
            "message_id": str(self.message_id) if self.message_id else None,
            "request_id": str(self.request_id),
            "request_type": self.request_type,
            "total_time_ms": self.total_time_ms,
            "ttfb_ms": self.llm_ttfb_ms if self.llm_ttfb_ms else None,
            "step_timings": self.get_step_timings(),
            "retrieval_metrics": self.get_retrieval_metrics_dict(),
            "context_metrics": self.context_metrics.to_dict() if self.context_metrics else {},
            "query_analysis": self.query_analysis_metrics.to_dict() if self.query_analysis_metrics else {},
            "status": self.status,
            "error_message": self.error_message,
            "error_type": self.error_type,
        }
