"""
Redis/ARQ Connection Settings

Provides Redis connection configuration for ARQ worker.
"""

from urllib.parse import urlparse

from arq.connections import RedisSettings

from src.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def parse_redis_url(url: str) -> dict:
    """Parse Redis URL into connection parameters."""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 6379,
        "password": parsed.password,
        "database": int(parsed.path.lstrip("/") or 0),
        "ssl": parsed.scheme == "rediss",
    }


def get_redis_settings() -> RedisSettings:
    """
    Get ARQ Redis connection settings.

    Returns:
        RedisSettings configured from environment variables.
    """
    redis_params = parse_redis_url(config.redis_url)

    settings = RedisSettings(
        host=redis_params["host"],
        port=redis_params["port"],
        password=redis_params["password"],
        database=redis_params["database"],
        ssl=redis_params["ssl"],
        conn_timeout=30,
        conn_retries=5,
        conn_retry_delay=1.0,
    )

    logger.debug(
        f"Redis settings configured: {redis_params['host']}:{redis_params['port']}/{redis_params['database']}"
    )

    return settings


class RedisHealthCheck:
    """Health check utilities for Redis connection."""

    @staticmethod
    async def check_connection() -> bool:
        """
        Check if Redis is reachable.

        Returns:
            True if connection successful, False otherwise.
        """
        import redis.asyncio as aioredis

        try:
            redis_params = parse_redis_url(config.redis_url)
            client = aioredis.Redis(
                host=redis_params["host"],
                port=redis_params["port"],
                password=redis_params["password"],
                db=redis_params["database"],
                ssl=redis_params["ssl"],
            )
            await client.ping()
            await client.aclose()
            logger.info("Redis health check passed")
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    @staticmethod
    async def get_queue_stats() -> dict[str, int]:
        """
        Get statistics about the ARQ queue.

        Returns:
            Dict with queue statistics.
        """
        import redis.asyncio as aioredis

        try:
            redis_params = parse_redis_url(config.redis_url)
            client = aioredis.Redis(
                host=redis_params["host"],
                port=redis_params["port"],
                password=redis_params["password"],
                db=redis_params["database"],
                ssl=redis_params["ssl"],
            )

            # ARQ stores jobs in sorted sets
            queue_key = f"{config.arq_queue_name}:queue"
            pending = await client.zcard(queue_key)

            # Get running jobs
            running_key = f"{config.arq_queue_name}:running"
            running = await client.zcard(running_key)

            # Get completed jobs (if tracking enabled)
            completed_key = f"{config.arq_queue_name}:complete"
            completed = await client.zcard(completed_key)

            await client.aclose()

            return {
                "pending": pending,
                "running": running,
                "completed": completed,
            }
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"pending": 0, "running": 0, "completed": 0}
