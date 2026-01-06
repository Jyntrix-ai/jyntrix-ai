"""Analytics API routes."""

import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.dependencies import CurrentUser, get_current_user, get_redis_client, get_supabase_admin_client
from src.schemas.analytics import (
    AnalyticsFilterParams,
    LatencyPercentilesResponse,
    RequestAnalyticsCreate,
    RequestAnalyticsListResponse,
    RequestAnalyticsResponse,
    RetrievalStatsResponse,
    SummaryStatsResponse,
    TimeSeriesDataResponse,
)
from src.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_analytics_service() -> AnalyticsService:
    """Get analytics service instance."""
    supabase = get_supabase_admin_client()
    try:
        redis = await get_redis_client()
    except Exception:
        redis = None
    return AnalyticsService(supabase=supabase, redis=redis)


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]


# ============================================================================
# List and Detail Endpoints
# ============================================================================


@router.get(
    "/requests",
    response_model=RequestAnalyticsListResponse,
    summary="List request analytics",
    description="Get paginated list of request analytics with optional filtering",
)
async def list_request_analytics(
    current_user: CurrentUser,
    analytics_service: AnalyticsServiceDep,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Records per page"),
    request_type: str | None = Query(default=None, description="Filter by request type"),
    request_status: str | None = Query(default=None, alias="status", description="Filter by status"),
    date_from: datetime | None = Query(default=None, description="Start date filter"),
    date_to: datetime | None = Query(default=None, description="End date filter"),
    conversation_id: UUID | None = Query(default=None, description="Filter by conversation"),
    min_latency_ms: float | None = Query(default=None, description="Minimum latency filter"),
    max_latency_ms: float | None = Query(default=None, description="Maximum latency filter"),
) -> RequestAnalyticsListResponse:
    """List request analytics with filtering and pagination."""
    try:
        filters = AnalyticsFilterParams(
            request_type=request_type,
            status=request_status,
            date_from=date_from,
            date_to=date_to,
            conversation_id=conversation_id,
            min_latency_ms=min_latency_ms,
            max_latency_ms=max_latency_ms,
        )
        return await analytics_service.list_requests(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            filters=filters,
        )
    except Exception as e:
        logger.error(f"List analytics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/requests/{analytics_id}",
    response_model=RequestAnalyticsResponse,
    summary="Get request analytics detail",
    description="Get detailed analytics for a specific request",
)
async def get_request_analytics(
    analytics_id: UUID,
    current_user: CurrentUser,
    analytics_service: AnalyticsServiceDep,
) -> RequestAnalyticsResponse:
    """Get detailed analytics for a specific request."""
    try:
        result = await analytics_service.get_request(
            user_id=current_user.id,
            analytics_id=analytics_id,
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analytics record not found",
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get analytics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Summary and Aggregation Endpoints
# ============================================================================


@router.get(
    "/summary",
    response_model=SummaryStatsResponse,
    summary="Get analytics summary",
    description="Get aggregated analytics summary for a time period",
)
async def get_analytics_summary(
    current_user: CurrentUser,
    analytics_service: AnalyticsServiceDep,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to aggregate"),
    request_type: str | None = Query(default=None, description="Filter by request type"),
) -> SummaryStatsResponse:
    """Get aggregated analytics summary."""
    try:
        return await analytics_service.get_summary(
            user_id=current_user.id,
            days=days,
            request_type=request_type,
        )
    except Exception as e:
        logger.error(f"Get summary error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/latency",
    response_model=LatencyPercentilesResponse,
    summary="Get latency percentiles",
    description="Get P50/P95/P99 latency percentiles for different operations",
)
async def get_latency_percentiles(
    current_user: CurrentUser,
    analytics_service: AnalyticsServiceDep,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
    request_type: str | None = Query(default=None, description="Filter by request type"),
    granularity: str = Query(default="day", pattern="^(hour|day|week)$", description="Time granularity"),
) -> LatencyPercentilesResponse:
    """Get latency percentiles with optional time-series breakdown."""
    try:
        return await analytics_service.get_latency_percentiles(
            user_id=current_user.id,
            days=days,
            request_type=request_type,
            granularity=granularity,
        )
    except Exception as e:
        logger.error(f"Get latency error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/retrieval",
    response_model=RetrievalStatsResponse,
    summary="Get retrieval quality stats",
    description="Get retrieval quality metrics (result counts, scores, deduplication)",
)
async def get_retrieval_stats(
    current_user: CurrentUser,
    analytics_service: AnalyticsServiceDep,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
) -> RetrievalStatsResponse:
    """Get retrieval quality statistics."""
    try:
        return await analytics_service.get_retrieval_stats(
            user_id=current_user.id,
            days=days,
        )
    except Exception as e:
        logger.error(f"Get retrieval stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/timeseries",
    response_model=TimeSeriesDataResponse,
    summary="Get time-series data",
    description="Get time-series data for dashboard charts",
)
async def get_timeseries_data(
    current_user: CurrentUser,
    analytics_service: AnalyticsServiceDep,
    metric: str = Query(..., description="Metric to retrieve: requests, latency, errors"),
    days: int = Query(default=7, ge=1, le=90, description="Number of days to include"),
    granularity: str = Query(default="hour", pattern="^(hour|day)$", description="Time granularity"),
) -> TimeSeriesDataResponse:
    """Get time-series data for charts."""
    try:
        return await analytics_service.get_timeseries(
            user_id=current_user.id,
            metric=metric,
            days=days,
            granularity=granularity,
        )
    except Exception as e:
        logger.error(f"Get timeseries error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Internal Recording Endpoint
# ============================================================================


@router.post(
    "/requests",
    response_model=RequestAnalyticsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record request analytics",
    description="Internal endpoint to record request analytics (used by chat service)",
    include_in_schema=False,  # Hide from public docs
)
async def record_request_analytics(
    request: RequestAnalyticsCreate,
    current_user: CurrentUser,
    analytics_service: AnalyticsServiceDep,
) -> RequestAnalyticsResponse:
    """Record analytics for a request (internal use)."""
    try:
        return await analytics_service.record_request(
            user_id=current_user.id,
            data=request,
        )
    except Exception as e:
        logger.error(f"Record analytics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/flush",
    summary="Force flush analytics buffer",
    description="Debug endpoint to force flush buffered analytics to database",
    include_in_schema=False,  # Hide from public docs
)
async def flush_analytics_buffer(
    current_user: CurrentUser,
) -> dict:
    """Force flush buffered analytics (debug/testing use)."""
    try:
        from src.analytics.emitter import _emitter, flush_analytics

        buffer_size = len(_emitter._buffer) if _emitter else 0
        await flush_analytics()

        return {
            "status": "flushed",
            "records_flushed": buffer_size,
            "message": f"Flushed {buffer_size} buffered analytics records",
        }
    except Exception as e:
        logger.error(f"Flush analytics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
