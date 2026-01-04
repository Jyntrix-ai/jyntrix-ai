"""Redis client configuration for caching and background tasks."""

from __future__ import annotations

import logging
from typing import Any, Set
from urllib.parse import urlparse

from redis.asyncio import Redis, ConnectionPool

from src.config import settings

logger = logging.getLogger(__name__)

# Global connection pool
_redis_pool: ConnectionPool | None = None


async def get_redis_pool() -> ConnectionPool:
    """Get or create Redis connection pool.

    Returns:
        Redis ConnectionPool
    """
    global _redis_pool

    if _redis_pool is None:
        parsed = urlparse(settings.redis_url)

        _redis_pool = ConnectionPool(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            db=settings.redis_db,
            password=settings.redis_password or parsed.password,
            decode_responses=True,
            max_connections=20,
        )

        logger.info(f"Redis connection pool created: {settings.redis_url}")

    return _redis_pool


async def get_redis_client() -> Redis:
    """Get Redis client instance.

    Returns:
        Configured Redis client
    """
    pool = await get_redis_pool()
    return Redis(connection_pool=pool)


class RedisManager:
    """Manager for Redis operations with caching utilities."""

    def __init__(self, client: Redis | None = None):
        """Initialize the manager.

        Args:
            client: Optional pre-configured client
        """
        self._client = client
        self.default_ttl = settings.redis_cache_ttl

    async def get_client(self) -> Redis:
        """Get or create the client."""
        if self._client is None:
            self._client = await get_redis_client()
        return self._client

    async def get(self, key: str) -> str | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        client = await self.get_client()
        return await client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None,
    ) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        client = await self.get_client()
        ttl = ttl or self.default_ttl
        return await client.setex(key, ttl, value)

    async def delete(self, key: str) -> int:
        """Delete key from cache.

        Args:
            key: Cache key

        Returns:
            Number of keys deleted
        """
        client = await self.get_client()
        return await client.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "user:123:*")

        Returns:
            Number of keys deleted
        """
        client = await self.get_client()
        keys = await client.keys(pattern)

        if keys:
            return await client.delete(*keys)
        return 0

    async def get_json(self, key: str) -> Any | None:
        """Get JSON value from cache.

        Args:
            key: Cache key

        Returns:
            Parsed JSON or None
        """
        import json

        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set JSON value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        import json

        json_str = json.dumps(value, default=str)
        return await self.set(key, json_str, ttl)

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter.

        Args:
            key: Counter key
            amount: Amount to increment

        Returns:
            New counter value
        """
        client = await self.get_client()
        return await client.incrby(key, amount)

    async def get_hash(self, key: str) -> dict[str, str]:
        """Get all fields from a hash.

        Args:
            key: Hash key

        Returns:
            Dict of field -> value
        """
        client = await self.get_client()
        return await client.hgetall(key)

    async def set_hash(self, key: str, mapping: dict[str, str]) -> int:
        """Set multiple hash fields.

        Args:
            key: Hash key
            mapping: Field -> value mapping

        Returns:
            Number of fields set
        """
        client = await self.get_client()
        return await client.hset(key, mapping=mapping)

    async def push_to_list(
        self,
        key: str,
        *values: str,
        left: bool = True,
    ) -> int:
        """Push values to a list.

        Args:
            key: List key
            values: Values to push
            left: Push to left (True) or right (False)

        Returns:
            List length after push
        """
        client = await self.get_client()
        if left:
            return await client.lpush(key, *values)
        return await client.rpush(key, *values)

    async def pop_from_list(
        self,
        key: str,
        left: bool = True,
    ) -> str | None:
        """Pop value from a list.

        Args:
            key: List key
            left: Pop from left (True) or right (False)

        Returns:
            Popped value or None
        """
        client = await self.get_client()
        if left:
            return await client.lpop(key)
        return await client.rpop(key)

    async def add_to_set(self, key: str, *members: str) -> int:
        """Add members to a set.

        Args:
            key: Set key
            members: Members to add

        Returns:
            Number of members added
        """
        client = await self.get_client()
        return await client.sadd(key, *members)

    async def get_set_members(self, key: str) -> set[str]:
        """Get all members of a set.

        Args:
            key: Set key

        Returns:
            Set of members
        """
        client = await self.get_client()
        return await client.smembers(key)

    async def check_connection(self) -> bool:
        """Check if Redis connection is working.

        Returns:
            True if connection is successful
        """
        try:
            client = await self.get_client()
            await client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis connection check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None


# Singleton instance
_redis_manager: RedisManager | None = None


async def get_redis_manager() -> RedisManager:
    """Get the singleton Redis manager.

    Returns:
        RedisManager instance
    """
    global _redis_manager

    if _redis_manager is None:
        _redis_manager = RedisManager()

    return _redis_manager


async def close_redis() -> None:
    """Close Redis connections on shutdown."""
    global _redis_pool, _redis_manager

    if _redis_manager:
        await _redis_manager.close()
        _redis_manager = None

    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None

    logger.info("Redis connections closed")
