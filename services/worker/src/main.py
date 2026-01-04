"""
ARQ Worker Entry Point

Defines the WorkerSettings class for ARQ worker configuration.
This module is the entry point for running the background worker.

Usage:
    arq src.main.WorkerSettings
"""

import asyncio
from datetime import timedelta
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from src.config import config
from src.db.redis import get_redis_settings
from src.db.qdrant import get_qdrant_client
from src.tasks.embedding_task import generate_batch_embeddings, generate_embedding
from src.tasks.extraction_task import extract_entities, extract_entities_batch
from src.tasks.summary_task import (
    summarize_batch,
    summarize_conversation,
    trigger_summary_for_idle_conversations,
)
from src.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    """
    Worker startup hook.

    Called once when the worker starts. Used to initialize shared resources
    that will be available in the ctx dict for all tasks.

    Args:
        ctx: Worker context dict that persists across tasks.
    """
    setup_logging()
    logger.info(f"Starting {config.worker_name} in {config.environment} mode")

    # Ensure Qdrant collection exists
    qdrant = get_qdrant_client()
    await qdrant.ensure_collection_exists()

    # Store in context for tasks to access
    ctx["worker_name"] = config.worker_name
    ctx["environment"] = config.environment

    logger.info(f"{config.worker_name} started successfully")


async def shutdown(ctx: dict[str, Any]) -> None:
    """
    Worker shutdown hook.

    Called once when the worker shuts down gracefully.

    Args:
        ctx: Worker context dict.
    """
    logger.info(f"Shutting down {config.worker_name}")

    # Cleanup any resources if needed
    # Note: ARQ handles Redis connection cleanup automatically

    logger.info(f"{config.worker_name} shut down complete")


async def on_job_start(ctx: dict[str, Any]) -> None:
    """
    Called before each job starts.

    Args:
        ctx: Job context containing job info.
    """
    job_id = ctx.get("job_id", "unknown")
    logger.debug(f"Starting job {job_id}")


async def on_job_end(ctx: dict[str, Any]) -> None:
    """
    Called after each job completes (success or failure).

    Args:
        ctx: Job context containing job info.
    """
    job_id = ctx.get("job_id", "unknown")
    logger.debug(f"Completed job {job_id}")


# Scheduled task: Check for idle conversations to summarize
async def scheduled_idle_summary(ctx: dict[str, Any]) -> dict[str, Any]:
    """Cron job to summarize idle conversations."""
    return await trigger_summary_for_idle_conversations(
        ctx,
        idle_minutes=30,
        limit=50,
    )


class WorkerSettings:
    """
    ARQ Worker Settings class.

    This class defines all the configuration for the ARQ worker including:
    - Redis connection settings
    - Task functions to register
    - Queue configuration
    - Retry settings
    - Cron jobs for scheduled tasks
    """

    # Redis connection
    redis_settings: RedisSettings = get_redis_settings()

    # Task functions to register with ARQ
    # Each function must be async and accept ctx as first parameter
    functions = [
        # Embedding tasks
        generate_embedding,
        generate_batch_embeddings,
        # Entity extraction tasks
        extract_entities,
        extract_entities_batch,
        # Summarization tasks
        summarize_conversation,
        summarize_batch,
        trigger_summary_for_idle_conversations,
    ]

    # Cron jobs for scheduled tasks
    cron_jobs = [
        # Check for idle conversations every 15 minutes
        cron(
            scheduled_idle_summary,
            minute={0, 15, 30, 45},
            run_at_startup=False,
        ),
    ]

    # Worker lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown
    on_job_start = on_job_start
    on_job_end = on_job_end

    # Queue configuration
    queue_name = config.arq_queue_name
    max_jobs = config.arq_max_jobs

    # Job timeout (in seconds)
    job_timeout = config.arq_job_timeout

    # Retry configuration
    max_tries = config.arq_max_retries if config.arq_retry_jobs else 1
    retry_delay = timedelta(seconds=30)

    # Health check interval
    health_check_interval = 30

    # Keep results for 1 hour
    keep_result = 3600

    # Keep result forever if job failed (for debugging)
    keep_result_forever = False

    # Allow abort signal
    allow_abort_jobs = True


# Convenience function to run worker programmatically
def run_worker() -> None:
    """Run the ARQ worker."""
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, "-m", "arq", "src.main.WorkerSettings"],
        check=True,
    )


# Health check endpoint for container orchestration
async def health_check() -> dict[str, Any]:
    """
    Perform health check on worker dependencies.

    Returns:
        Health status dict.
    """
    from src.db.redis import RedisHealthCheck
    from src.db.qdrant import get_qdrant_client

    health = {
        "status": "healthy",
        "checks": {},
    }

    # Check Redis
    redis_ok = await RedisHealthCheck.check_connection()
    health["checks"]["redis"] = "ok" if redis_ok else "error"

    # Check Qdrant
    qdrant = get_qdrant_client()
    qdrant_info = await qdrant.get_collection_info()
    health["checks"]["qdrant"] = "ok" if qdrant_info else "error"

    # Overall status
    if not all(v == "ok" for v in health["checks"].values()):
        health["status"] = "unhealthy"

    return health


if __name__ == "__main__":
    # Allow running directly with: python -m src.main
    run_worker()
