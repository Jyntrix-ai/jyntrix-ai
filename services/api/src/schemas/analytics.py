"""Analytics schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Request Schemas
# ============================================================================


class AnalyticsFilterParams(BaseModel):
    """Filter parameters for analytics queries."""

    request_type: str | None = Field(
        default=None,
        description="Filter by request type (chat_stream, chat_complete, memory_search)",
    )
    status: str | None = Field(
        default=None,
        description="Filter by status (success, partial, error, timeout)",
    )
    date_from: datetime | None = Field(
        default=None,
        description="Start date filter (inclusive)",
    )
    date_to: datetime | None = Field(
        default=None,
        description="End date filter (inclusive)",
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Filter by conversation ID",
    )
    min_latency_ms: float | None = Field(
        default=None,
        description="Minimum total latency in milliseconds",
    )
    max_latency_ms: float | None = Field(
        default=None,
        description="Maximum total latency in milliseconds",
    )


# ============================================================================
# Sub-schemas for Nested Data
# ============================================================================


class StepTimings(BaseModel):
    """Individual step timing breakdown."""

    setup_time: float | None = Field(default=None, description="Setup phase time (ms)")
    query_analysis_time: float | None = Field(default=None, description="Query analysis time (ms)")
    vector_search_time: float | None = Field(default=None, description="Vector search time (ms)")
    keyword_search_time: float | None = Field(default=None, description="Keyword search time (ms)")
    graph_search_time: float | None = Field(default=None, description="Graph search time (ms)")
    profile_retrieval_time: float | None = Field(default=None, description="Profile retrieval time (ms)")
    recent_context_time: float | None = Field(default=None, description="Recent context time (ms)")
    total_retrieval_time: float | None = Field(default=None, description="Total retrieval time (parallel max) (ms)")
    ranking_time: float | None = Field(default=None, description="Hybrid ranking time (ms)")
    context_building_time: float | None = Field(default=None, description="Context building time (ms)")
    llm_ttfb: float | None = Field(default=None, description="LLM time to first byte (ms)")
    llm_total_time: float | None = Field(default=None, description="LLM total generation time (ms)")
    save_response_time: float | None = Field(default=None, description="Save response time (ms)")


class ScoreDistribution(BaseModel):
    """Score distribution statistics."""

    min: float = Field(default=0.0, description="Minimum score")
    max: float = Field(default=0.0, description="Maximum score")
    avg: float = Field(default=0.0, description="Average score")


class RetrievalMetricsSchema(BaseModel):
    """Retrieval quality metrics."""

    vector_results_count: int = Field(default=0, description="Number of vector search results")
    keyword_results_count: int = Field(default=0, description="Number of keyword search results")
    graph_results_count: int = Field(default=0, description="Number of graph search results")
    profile_results_count: int = Field(default=0, description="Number of profile memories retrieved")
    recent_results_count: int = Field(default=0, description="Number of recent context results")
    total_raw_results: int = Field(default=0, description="Total results before deduplication")
    post_dedup_count: int = Field(default=0, description="Results after deduplication")
    deduplication_removed: int = Field(default=0, description="Number of duplicates removed")
    score_distribution: dict[str, ScoreDistribution] = Field(
        default_factory=dict,
        description="Score distribution by strategy",
    )
    memories_by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Count of memories by type (profile, semantic, etc.)",
    )


class ContextMetricsSchema(BaseModel):
    """Context building metrics."""

    profile_tokens_used: int = Field(default=0, description="Tokens used for profile memories")
    semantic_tokens_used: int = Field(default=0, description="Tokens used for semantic memories")
    episodic_tokens_used: int = Field(default=0, description="Tokens used for episodic memories")
    procedural_tokens_used: int = Field(default=0, description="Tokens used for procedural memories")
    entity_tokens_used: int = Field(default=0, description="Tokens used for entity context")
    total_context_tokens: int = Field(default=0, description="Total tokens in context")
    token_budget_max: int = Field(default=0, description="Maximum token budget")
    truncation_occurred: bool = Field(default=False, description="Whether context was truncated")
    memories_included: int = Field(default=0, description="Number of memories included")
    memories_truncated: int = Field(default=0, description="Number of memories truncated")


class QueryAnalysisSchema(BaseModel):
    """Query analysis results."""

    intent: str | None = Field(default=None, description="Detected intent (recall, question, command, conversation)")
    requires_memory: bool = Field(default=True, description="Whether memory retrieval was needed")
    keywords_count: int = Field(default=0, description="Number of keywords extracted")
    entities_count: int = Field(default=0, description="Number of entities detected")
    memory_types_needed: list[str] = Field(default_factory=list, description="Memory types needed for query")


# ============================================================================
# Create/Record Schema
# ============================================================================


class RequestAnalyticsCreate(BaseModel):
    """Schema for recording request analytics."""

    request_id: str = Field(..., description="Correlation ID from X-Request-ID")
    request_type: str = Field(..., description="Type of request (chat_stream, chat_complete, etc.)")
    conversation_id: UUID | None = Field(default=None, description="Associated conversation ID")
    message_id: UUID | None = Field(default=None, description="Associated message ID")

    total_time_ms: float = Field(..., description="Total request time in milliseconds")
    ttfb_ms: float | None = Field(default=None, description="Time to first byte in milliseconds")

    step_timings: StepTimings = Field(default_factory=StepTimings, description="Per-step timing breakdown")
    retrieval_metrics: RetrievalMetricsSchema = Field(
        default_factory=RetrievalMetricsSchema,
        description="Retrieval quality metrics",
    )
    context_metrics: ContextMetricsSchema = Field(
        default_factory=ContextMetricsSchema,
        description="Context building metrics",
    )
    query_analysis: QueryAnalysisSchema = Field(
        default_factory=QueryAnalysisSchema,
        description="Query analysis results",
    )

    status: str = Field(default="success", description="Request status (success, partial, error, timeout)")
    error_message: str | None = Field(default=None, description="Error message if failed")
    error_type: str | None = Field(default=None, description="Error type/category")


# ============================================================================
# Response Schemas
# ============================================================================


class RequestAnalyticsResponse(BaseModel):
    """Response schema for a single analytics record."""

    id: UUID = Field(..., description="Analytics record ID")
    user_id: str = Field(..., description="User ID")
    request_id: str = Field(..., description="Request correlation ID")
    request_type: str = Field(..., description="Type of request")
    conversation_id: UUID | None = Field(default=None, description="Associated conversation ID")
    message_id: UUID | None = Field(default=None, description="Associated message ID")

    total_time_ms: float = Field(..., description="Total request time in milliseconds")
    ttfb_ms: float | None = Field(default=None, description="Time to first byte")

    step_timings: dict[str, Any] = Field(default_factory=dict, description="Per-step timing breakdown")
    retrieval_metrics: dict[str, Any] = Field(default_factory=dict, description="Retrieval quality metrics")
    context_metrics: dict[str, Any] = Field(default_factory=dict, description="Context building metrics")
    query_analysis: dict[str, Any] = Field(default_factory=dict, description="Query analysis results")

    status: str = Field(..., description="Request status")
    error_message: str | None = Field(default=None, description="Error message if failed")
    error_type: str | None = Field(default=None, description="Error type/category")

    created_at: datetime = Field(..., description="When the request was recorded")

    class Config:
        """Pydantic config."""

        from_attributes = True


class RequestAnalyticsListResponse(BaseModel):
    """Response schema for listing analytics."""

    analytics: list[RequestAnalyticsResponse] = Field(
        default_factory=list,
        description="List of analytics records",
    )
    total: int = Field(..., description="Total number of records matching filters")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of records per page")
    has_more: bool = Field(..., description="Whether there are more pages")


# ============================================================================
# Latency Percentile Schemas
# ============================================================================


class LatencyPercentiles(BaseModel):
    """Latency percentile values."""

    p50: float = Field(..., description="50th percentile (median)")
    p95: float = Field(..., description="95th percentile")
    p99: float = Field(..., description="99th percentile")
    avg: float = Field(..., description="Average value")
    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")
    sample_count: int = Field(..., description="Number of samples")


class LatencyPercentilesResponse(BaseModel):
    """Response for latency percentiles endpoint."""

    total_time: LatencyPercentiles = Field(..., description="Total request time percentiles")
    ttfb: LatencyPercentiles | None = Field(default=None, description="Time to first byte percentiles")
    retrieval: LatencyPercentiles | None = Field(default=None, description="Retrieval time percentiles")
    llm: LatencyPercentiles | None = Field(default=None, description="LLM time percentiles")
    ranking: LatencyPercentiles | None = Field(default=None, description="Ranking time percentiles")
    context_building: LatencyPercentiles | None = Field(default=None, description="Context building percentiles")

    # Optional time-series breakdown
    timeseries: list[dict[str, Any]] | None = Field(
        default=None,
        description="Time-series breakdown of percentiles",
    )

    period_days: int = Field(..., description="Number of days in the analysis period")
    request_type: str | None = Field(default=None, description="Request type filter applied")


# ============================================================================
# Summary Stats Schemas
# ============================================================================


class SummaryStatsResponse(BaseModel):
    """Response for summary statistics."""

    period_days: int = Field(..., description="Number of days in the summary period")
    total_requests: int = Field(..., description="Total number of requests")
    successful_requests: int = Field(..., description="Number of successful requests")
    error_requests: int = Field(..., description="Number of failed requests")
    error_rate: float = Field(..., description="Error rate (0-1)")

    avg_latency_ms: float = Field(..., description="Average total latency")
    p50_latency_ms: float = Field(..., description="Median total latency")
    p95_latency_ms: float = Field(..., description="95th percentile total latency")

    avg_ttfb_ms: float | None = Field(default=None, description="Average time to first byte")

    requests_by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Request counts by type",
    )
    requests_by_day: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Request counts by day",
    )

    avg_retrieval_results: float = Field(default=0.0, description="Average number of retrieval results")
    avg_context_tokens: float = Field(default=0.0, description="Average context tokens used")

    intent_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of query intents",
    )


# ============================================================================
# Retrieval Stats Schemas
# ============================================================================


class RetrievalStatsResponse(BaseModel):
    """Response for retrieval quality statistics."""

    period_days: int = Field(..., description="Number of days in the analysis period")
    total_requests: int = Field(..., description="Total number of requests analyzed")

    avg_vector_results: float = Field(default=0.0, description="Average vector search results")
    avg_keyword_results: float = Field(default=0.0, description="Average keyword search results")
    avg_graph_results: float = Field(default=0.0, description="Average graph search results")
    avg_total_results: float = Field(default=0.0, description="Average total results")

    avg_deduplication_rate: float = Field(default=0.0, description="Average deduplication rate")

    avg_combined_score: float = Field(default=0.0, description="Average combined ranking score")
    score_distribution: dict[str, ScoreDistribution] = Field(
        default_factory=dict,
        description="Score distribution by strategy",
    )

    memories_by_type_total: dict[str, int] = Field(
        default_factory=dict,
        description="Total memories used by type",
    )
    avg_memories_by_type: dict[str, float] = Field(
        default_factory=dict,
        description="Average memories per request by type",
    )

    avg_context_tokens: float = Field(default=0.0, description="Average context tokens used")
    truncation_rate: float = Field(default=0.0, description="Rate of context truncation")


# ============================================================================
# Time Series Schemas
# ============================================================================


class TimeSeriesDataPoint(BaseModel):
    """Single data point in time series."""

    timestamp: datetime = Field(..., description="Timestamp for this data point")
    value: float = Field(..., description="The metric value")
    count: int | None = Field(default=None, description="Optional count for this period")


class TimeSeriesDataResponse(BaseModel):
    """Response for time-series data."""

    metric: str = Field(..., description="Name of the metric")
    period_days: int = Field(..., description="Number of days in the time series")
    granularity: str = Field(..., description="Time granularity (hour, day)")
    data_points: list[TimeSeriesDataPoint] = Field(
        default_factory=list,
        description="Time series data points",
    )
