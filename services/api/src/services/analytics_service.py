"""Analytics service for recording and querying analytics data."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from supabase import Client as SupabaseClient

from src.schemas.analytics import (
    AnalyticsFilterParams,
    LatencyPercentiles,
    LatencyPercentilesResponse,
    RetrievalStatsResponse,
    RequestAnalyticsCreate,
    RequestAnalyticsListResponse,
    RequestAnalyticsResponse,
    ScoreDistribution,
    SummaryStatsResponse,
    TimeSeriesDataPoint,
    TimeSeriesDataResponse,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics operations.

    Provides methods for recording, querying, and aggregating
    analytics data from request_analytics table.
    """

    def __init__(self, supabase: SupabaseClient, redis: Redis | None = None):
        """Initialize analytics service.

        Args:
            supabase: Supabase client for database operations
            redis: Optional Redis client for caching
        """
        self.supabase = supabase
        self.redis = redis
        self.cache_ttl = 300  # 5 minutes for analytics cache

    async def record_request(
        self,
        user_id: str,
        data: RequestAnalyticsCreate,
    ) -> RequestAnalyticsResponse:
        """Record analytics for a request.

        Args:
            user_id: The user ID
            data: The analytics data to record

        Returns:
            The created analytics record
        """
        record = {
            "user_id": user_id,
            "request_id": data.request_id,
            "request_type": data.request_type,
            "conversation_id": str(data.conversation_id) if data.conversation_id else None,
            "message_id": str(data.message_id) if data.message_id else None,
            "total_time_ms": data.total_time_ms,
            "ttfb_ms": data.ttfb_ms,
            "step_timings": data.step_timings.model_dump(exclude_none=True),
            "retrieval_metrics": data.retrieval_metrics.model_dump(),
            "context_metrics": data.context_metrics.model_dump(),
            "query_analysis": data.query_analysis.model_dump(),
            "status": data.status,
            "error_message": data.error_message,
            "error_type": data.error_type,
        }

        response = self.supabase.table("request_analytics").insert(record).execute()

        # Invalidate cached summaries for this user
        if self.redis:
            await self._invalidate_cache(user_id)

        return RequestAnalyticsResponse(**response.data[0])

    async def list_requests(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        filters: AnalyticsFilterParams | None = None,
    ) -> RequestAnalyticsListResponse:
        """List analytics with filtering and pagination.

        Args:
            user_id: The user ID
            page: Page number (1-indexed)
            page_size: Number of records per page
            filters: Optional filter parameters

        Returns:
            Paginated list of analytics records
        """
        offset = (page - 1) * page_size
        filters = filters or AnalyticsFilterParams()

        query = (
            self.supabase.table("request_analytics")
            .select("*", count="exact")
            .eq("user_id", user_id)
        )

        # Apply filters
        if filters.request_type:
            query = query.eq("request_type", filters.request_type)
        if filters.status:
            query = query.eq("status", filters.status)
        if filters.date_from:
            query = query.gte("created_at", filters.date_from.isoformat())
        if filters.date_to:
            query = query.lte("created_at", filters.date_to.isoformat())
        if filters.conversation_id:
            query = query.eq("conversation_id", str(filters.conversation_id))
        if filters.min_latency_ms is not None:
            query = query.gte("total_time_ms", filters.min_latency_ms)
        if filters.max_latency_ms is not None:
            query = query.lte("total_time_ms", filters.max_latency_ms)

        response = (
            query
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

        analytics = [RequestAnalyticsResponse(**r) for r in response.data or []]
        total = response.count or len(analytics)

        return RequestAnalyticsListResponse(
            analytics=analytics,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )

    async def get_request(
        self,
        user_id: str,
        analytics_id: UUID,
    ) -> RequestAnalyticsResponse | None:
        """Get single analytics record.

        Args:
            user_id: The user ID
            analytics_id: The analytics record ID

        Returns:
            The analytics record, or None if not found
        """
        response = (
            self.supabase.table("request_analytics")
            .select("*")
            .eq("id", str(analytics_id))
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if response.data:
            return RequestAnalyticsResponse(**response.data)
        return None

    async def get_summary(
        self,
        user_id: str,
        days: int = 7,
        request_type: str | None = None,
    ) -> SummaryStatsResponse:
        """Get aggregated summary statistics.

        Args:
            user_id: The user ID
            days: Number of days to include
            request_type: Optional filter by request type

        Returns:
            Summary statistics
        """
        cache_key = f"analytics:summary:{user_id}:{days}:{request_type or 'all'}"

        # Try cache first
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return SummaryStatsResponse(**json.loads(cached))

        # Build query
        date_cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        query = (
            self.supabase.table("request_analytics")
            .select("*")
            .eq("user_id", user_id)
            .gte("created_at", date_cutoff)
        )

        if request_type:
            query = query.eq("request_type", request_type)

        response = query.execute()
        records = response.data or []

        if not records:
            return SummaryStatsResponse(
                period_days=days,
                total_requests=0,
                successful_requests=0,
                error_requests=0,
                error_rate=0.0,
                avg_latency_ms=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
            )

        # Calculate statistics
        total = len(records)
        successful = sum(1 for r in records if r["status"] == "success")
        errors = sum(1 for r in records if r["status"] == "error")
        latencies = [r["total_time_ms"] for r in records]
        ttfbs = [r["ttfb_ms"] for r in records if r.get("ttfb_ms")]

        # Sort for percentiles
        latencies.sort()

        # Calculate percentiles
        p50_idx = int(len(latencies) * 0.5)
        p95_idx = int(len(latencies) * 0.95)

        # Count by type
        type_counts: dict[str, int] = {}
        for r in records:
            rt = r["request_type"]
            type_counts[rt] = type_counts.get(rt, 0) + 1

        # Count by day
        day_counts: dict[str, int] = {}
        for r in records:
            day = r["created_at"][:10]  # YYYY-MM-DD
            day_counts[day] = day_counts.get(day, 0) + 1

        requests_by_day = [
            {"date": date, "count": count}
            for date, count in sorted(day_counts.items())
        ]

        # Intent distribution
        intent_counts: dict[str, int] = {}
        for r in records:
            qa = r.get("query_analysis") or {}
            intent = qa.get("intent", "unknown")
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        # Retrieval and context averages
        retrieval_totals = [
            (r.get("retrieval_metrics") or {}).get("total_raw_results", 0)
            for r in records
        ]
        context_tokens = [
            (r.get("context_metrics") or {}).get("total_context_tokens", 0)
            for r in records
        ]

        result = SummaryStatsResponse(
            period_days=days,
            total_requests=total,
            successful_requests=successful,
            error_requests=errors,
            error_rate=errors / total if total > 0 else 0.0,
            avg_latency_ms=sum(latencies) / len(latencies),
            p50_latency_ms=latencies[p50_idx] if latencies else 0.0,
            p95_latency_ms=latencies[p95_idx] if latencies else 0.0,
            avg_ttfb_ms=sum(ttfbs) / len(ttfbs) if ttfbs else None,
            requests_by_type=type_counts,
            requests_by_day=requests_by_day,
            avg_retrieval_results=sum(retrieval_totals) / len(retrieval_totals) if retrieval_totals else 0.0,
            avg_context_tokens=sum(context_tokens) / len(context_tokens) if context_tokens else 0.0,
            intent_distribution=intent_counts,
        )

        # Cache result
        if self.redis:
            await self.redis.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(result.model_dump(), default=str),
            )

        return result

    async def get_latency_percentiles(
        self,
        user_id: str,
        days: int = 7,
        request_type: str | None = None,
        granularity: str = "day",
    ) -> LatencyPercentilesResponse:
        """Get latency percentiles.

        Args:
            user_id: The user ID
            days: Number of days to include
            request_type: Optional filter by request type
            granularity: Time granularity (hour, day, week)

        Returns:
            Latency percentiles
        """
        # Use the database function for efficient calculation
        try:
            response = self.supabase.rpc(
                "get_latency_percentiles",
                {
                    "p_user_id": user_id,
                    "p_days": days,
                    "p_request_type": request_type,
                },
            ).execute()

            metrics_data = {row["metric_name"]: row for row in response.data or []}
        except Exception as e:
            logger.warning(f"RPC failed, falling back to manual calculation: {e}")
            metrics_data = await self._calculate_percentiles_manually(user_id, days, request_type)

        def build_percentiles(data: dict[str, Any] | None) -> LatencyPercentiles | None:
            if not data or data.get("sample_count", 0) == 0:
                return None
            return LatencyPercentiles(
                p50=data.get("p50", 0) or 0,
                p95=data.get("p95", 0) or 0,
                p99=data.get("p99", 0) or 0,
                avg=data.get("avg_value", 0) or 0,
                min=data.get("min_value", 0) or 0,
                max=data.get("max_value", 0) or 0,
                sample_count=data.get("sample_count", 0) or 0,
            )

        return LatencyPercentilesResponse(
            total_time=build_percentiles(metrics_data.get("total_time")) or LatencyPercentiles(
                p50=0, p95=0, p99=0, avg=0, min=0, max=0, sample_count=0
            ),
            ttfb=build_percentiles(metrics_data.get("ttfb")),
            retrieval=build_percentiles(metrics_data.get("retrieval")),
            llm=build_percentiles(metrics_data.get("llm")),
            ranking=build_percentiles(metrics_data.get("ranking")),
            context_building=build_percentiles(metrics_data.get("context_building")),
            period_days=days,
            request_type=request_type,
        )

    async def _calculate_percentiles_manually(
        self,
        user_id: str,
        days: int,
        request_type: str | None,
    ) -> dict[str, dict[str, Any]]:
        """Fallback manual percentile calculation."""
        date_cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        query = (
            self.supabase.table("request_analytics")
            .select("total_time_ms, ttfb_ms, step_timings")
            .eq("user_id", user_id)
            .eq("status", "success")
            .gte("created_at", date_cutoff)
        )

        if request_type:
            query = query.eq("request_type", request_type)

        response = query.execute()
        records = response.data or []

        def calc_percentiles(values: list[float]) -> dict[str, Any]:
            if not values:
                return {"sample_count": 0}
            values.sort()
            n = len(values)
            return {
                "p50": values[int(n * 0.5)],
                "p95": values[int(n * 0.95)],
                "p99": values[int(n * 0.99)],
                "avg_value": sum(values) / n,
                "min_value": min(values),
                "max_value": max(values),
                "sample_count": n,
            }

        total_times = [r["total_time_ms"] for r in records]
        ttfbs = [r["ttfb_ms"] for r in records if r.get("ttfb_ms")]
        retrievals = [
            (r.get("step_timings") or {}).get("total_retrieval_time")
            for r in records
            if (r.get("step_timings") or {}).get("total_retrieval_time")
        ]
        llms = [
            (r.get("step_timings") or {}).get("llm_total_time")
            for r in records
            if (r.get("step_timings") or {}).get("llm_total_time")
        ]

        return {
            "total_time": calc_percentiles(total_times),
            "ttfb": calc_percentiles(ttfbs),
            "retrieval": calc_percentiles(retrievals),
            "llm": calc_percentiles(llms),
        }

    async def get_retrieval_stats(
        self,
        user_id: str,
        days: int = 7,
    ) -> RetrievalStatsResponse:
        """Get retrieval quality statistics.

        Args:
            user_id: The user ID
            days: Number of days to include

        Returns:
            Retrieval quality statistics
        """
        date_cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        response = (
            self.supabase.table("request_analytics")
            .select("retrieval_metrics, context_metrics")
            .eq("user_id", user_id)
            .gte("created_at", date_cutoff)
            .execute()
        )

        records = response.data or []

        if not records:
            return RetrievalStatsResponse(
                period_days=days,
                total_requests=0,
            )

        # Aggregate metrics
        vector_results: list[int] = []
        keyword_results: list[int] = []
        graph_results: list[int] = []
        total_results: list[int] = []
        context_tokens: list[int] = []
        truncations: list[bool] = []
        memories_by_type: dict[str, int] = {}

        for r in records:
            rm = r.get("retrieval_metrics") or {}
            cm = r.get("context_metrics") or {}

            vector_results.append(rm.get("vector_results_count", 0))
            keyword_results.append(rm.get("keyword_results_count", 0))
            graph_results.append(rm.get("graph_results_count", 0))
            total_results.append(rm.get("total_raw_results", 0))
            context_tokens.append(cm.get("total_context_tokens", 0))
            truncations.append(cm.get("truncation_occurred", False))

            # Aggregate memory types
            for mt, count in rm.get("memories_by_type", {}).items():
                memories_by_type[mt] = memories_by_type.get(mt, 0) + count

        n = len(records)

        return RetrievalStatsResponse(
            period_days=days,
            total_requests=n,
            avg_vector_results=sum(vector_results) / n if n else 0,
            avg_keyword_results=sum(keyword_results) / n if n else 0,
            avg_graph_results=sum(graph_results) / n if n else 0,
            avg_total_results=sum(total_results) / n if n else 0,
            avg_deduplication_rate=0.0,  # Would need post_dedup_count to calculate
            avg_combined_score=0.0,  # Would need score data
            memories_by_type_total=memories_by_type,
            avg_memories_by_type={
                mt: count / n for mt, count in memories_by_type.items()
            } if n else {},
            avg_context_tokens=sum(context_tokens) / n if n else 0,
            truncation_rate=sum(1 for t in truncations if t) / n if n else 0,
        )

    async def get_timeseries(
        self,
        user_id: str,
        metric: str,
        days: int = 7,
        granularity: str = "hour",
    ) -> TimeSeriesDataResponse:
        """Get time-series data for charts.

        Args:
            user_id: The user ID
            metric: Metric to retrieve (requests, latency, errors)
            days: Number of days to include
            granularity: Time granularity (hour, day)

        Returns:
            Time series data
        """
        date_cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        response = (
            self.supabase.table("request_analytics")
            .select("created_at, total_time_ms, status")
            .eq("user_id", user_id)
            .gte("created_at", date_cutoff)
            .order("created_at")
            .execute()
        )

        records = response.data or []

        # Group by time bucket
        buckets: dict[str, list[dict[str, Any]]] = {}
        for r in records:
            dt = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            if granularity == "hour":
                bucket = dt.strftime("%Y-%m-%d %H:00:00")
            else:
                bucket = dt.strftime("%Y-%m-%d")
            if bucket not in buckets:
                buckets[bucket] = []
            buckets[bucket].append(r)

        # Calculate metric for each bucket
        data_points: list[TimeSeriesDataPoint] = []
        for bucket, bucket_records in sorted(buckets.items()):
            timestamp = datetime.fromisoformat(bucket)
            count = len(bucket_records)

            if metric == "requests":
                value = float(count)
            elif metric == "latency":
                latencies = [r["total_time_ms"] for r in bucket_records]
                value = sum(latencies) / len(latencies) if latencies else 0
            elif metric == "errors":
                value = float(sum(1 for r in bucket_records if r["status"] == "error"))
            else:
                value = float(count)

            data_points.append(TimeSeriesDataPoint(
                timestamp=timestamp,
                value=value,
                count=count,
            ))

        return TimeSeriesDataResponse(
            metric=metric,
            period_days=days,
            granularity=granularity,
            data_points=data_points,
        )

    async def _invalidate_cache(self, user_id: str) -> None:
        """Invalidate cached analytics for a user.

        Args:
            user_id: The user ID
        """
        if not self.redis:
            return

        pattern = f"analytics:*:{user_id}:*"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
