"""Analytics background tasks for aggregation and cleanup.

These tasks run periodically to:
1. Aggregate daily analytics for dashboard performance
2. Clean up old analytics data based on retention policy
"""

import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


async def aggregate_daily_analytics(
    ctx: dict[str, Any],
    target_date: str | None = None,
) -> dict[str, Any]:
    """Aggregate analytics for a specific day.

    This task pre-computes daily statistics and stores them in the
    analytics_daily_aggregates table for faster dashboard queries.

    Should be run daily via cron (e.g., at 01:00 UTC for previous day).

    Args:
        ctx: ARQ context with Redis pool
        target_date: Date to aggregate (YYYY-MM-DD), defaults to yesterday

    Returns:
        Dict with success status and rows affected
    """
    from src.db.supabase import get_supabase_admin_client

    try:
        supabase = get_supabase_admin_client()

        # Default to yesterday if no date provided
        if target_date:
            agg_date = target_date
        else:
            agg_date = (date.today() - timedelta(days=1)).isoformat()

        logger.info(f"Aggregating analytics for date: {agg_date}")

        # Call the aggregation function
        response = supabase.rpc(
            "aggregate_daily_analytics",
            {"p_date": agg_date},
        ).execute()

        rows_affected = response.data if response.data else 0

        logger.info(
            f"Analytics aggregation complete for {agg_date}: "
            f"{rows_affected} user(s) processed"
        )

        return {
            "success": True,
            "date": agg_date,
            "rows_affected": rows_affected,
        }

    except Exception as e:
        logger.error(f"Analytics aggregation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "date": target_date,
        }


async def cleanup_old_analytics(
    ctx: dict[str, Any],
    retention_days: int | None = None,
) -> dict[str, Any]:
    """Clean up old analytics data based on retention policy.

    This task deletes analytics records older than the retention period
    to manage storage and comply with data policies.

    Should be run weekly via cron (e.g., Sunday at 02:00 UTC).

    Args:
        ctx: ARQ context with Redis pool
        retention_days: Days to retain data (defaults to config value)

    Returns:
        Dict with success status and records deleted
    """
    from src.config import settings
    from src.db.supabase import get_supabase_admin_client

    try:
        supabase = get_supabase_admin_client()

        # Use config default if not specified
        if retention_days is None:
            retention_days = getattr(settings, "analytics_retention_days", 90)

        logger.info(f"Cleaning up analytics older than {retention_days} days")

        # Call the cleanup function
        response = supabase.rpc(
            "cleanup_old_analytics",
            {"p_retention_days": retention_days},
        ).execute()

        deleted_count = response.data if response.data else 0

        logger.info(
            f"Analytics cleanup complete: {deleted_count} record(s) deleted "
            f"(retention: {retention_days} days)"
        )

        return {
            "success": True,
            "retention_days": retention_days,
            "records_deleted": deleted_count,
        }

    except Exception as e:
        logger.error(f"Analytics cleanup failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "retention_days": retention_days,
        }


async def process_analytics_stream(
    ctx: dict[str, Any],
    batch_size: int = 100,
) -> dict[str, Any]:
    """Process analytics from Redis stream and persist to database.

    This task reads analytics records from the Redis stream buffer
    and writes them to the database in batches.

    Should be run frequently (e.g., every 30 seconds) or on demand.

    Args:
        ctx: ARQ context with Redis pool
        batch_size: Maximum records to process per run

    Returns:
        Dict with success status and records processed
    """
    from src.db.supabase import get_supabase_admin_client

    try:
        redis = ctx.get("redis")
        if not redis:
            logger.warning("Redis not available for analytics stream processing")
            return {"success": False, "error": "Redis not available"}

        supabase = get_supabase_admin_client()

        # Read from Redis stream
        stream_key = "analytics:requests"
        entries = await redis.xread({stream_key: "0-0"}, count=batch_size)

        if not entries:
            return {"success": True, "records_processed": 0}

        records = []
        entry_ids = []

        for stream_name, stream_entries in entries:
            for entry_id, data in stream_entries:
                entry_ids.append(entry_id)
                try:
                    import json
                    record_data = json.loads(data.get(b"data", b"{}").decode())
                    records.append(record_data)
                except Exception as e:
                    logger.warning(f"Failed to parse analytics entry {entry_id}: {e}")

        if records:
            # Batch insert to database
            supabase.table("request_analytics").insert(records).execute()

            # Remove processed entries from stream
            if entry_ids:
                await redis.xdel(stream_key, *entry_ids)

        logger.info(f"Processed {len(records)} analytics records from stream")

        return {
            "success": True,
            "records_processed": len(records),
        }

    except Exception as e:
        logger.error(f"Analytics stream processing failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }
