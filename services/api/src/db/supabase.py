"""Supabase client configuration."""

import logging
from functools import lru_cache

from supabase import Client, create_client

from src.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get Supabase client with anonymous key.

    This client is used for user-facing operations where
    the user's JWT token provides authentication.

    Returns:
        Configured Supabase client
    """
    try:
        client = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_anon_key,
        )
        logger.info("Supabase client initialized with anon key")
        return client

    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        raise


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
    """Get Supabase client with service role key.

    This client has elevated privileges and should only be used
    for administrative operations like:
    - User management
    - Bypassing RLS policies
    - Background jobs

    Returns:
        Configured Supabase admin client
    """
    try:
        client = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_service_key,
        )
        logger.info("Supabase admin client initialized with service role key")
        return client

    except Exception as e:
        logger.error(f"Failed to initialize Supabase admin client: {e}")
        raise


class SupabaseManager:
    """Manager for Supabase connections and operations."""

    def __init__(self):
        """Initialize the manager."""
        self._client: Client | None = None
        self._admin_client: Client | None = None

    @property
    def client(self) -> Client:
        """Get or create the standard client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    @property
    def admin_client(self) -> Client:
        """Get or create the admin client."""
        if self._admin_client is None:
            self._admin_client = get_supabase_admin_client()
        return self._admin_client

    async def check_connection(self) -> bool:
        """Check if Supabase connection is working.

        Returns:
            True if connection is successful
        """
        try:
            # Try a simple query
            self.client.table("profiles").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase connection check failed: {e}")
            return False

    def get_storage_bucket(self, bucket_name: str):
        """Get a storage bucket client.

        Args:
            bucket_name: Name of the storage bucket

        Returns:
            Storage bucket client
        """
        return self.client.storage.from_(bucket_name)

    async def run_rpc(self, function_name: str, params: dict | None = None):
        """Run a Supabase RPC function.

        Args:
            function_name: Name of the function to call
            params: Optional parameters for the function

        Returns:
            Function result
        """
        try:
            response = self.client.rpc(function_name, params or {}).execute()
            return response.data
        except Exception as e:
            logger.error(f"RPC call {function_name} failed: {e}")
            raise


# Singleton instance
_supabase_manager: SupabaseManager | None = None


def get_supabase_manager() -> SupabaseManager:
    """Get the singleton Supabase manager.

    Returns:
        SupabaseManager instance
    """
    global _supabase_manager

    if _supabase_manager is None:
        _supabase_manager = SupabaseManager()

    return _supabase_manager
