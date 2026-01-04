"""
Worker Configuration Module

Loads all worker settings from environment variables using Pydantic Settings.
Provides centralized configuration for Redis, Supabase, Qdrant, and Gemini.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> Path:
    """Find .env file by traversing up from current directory."""
    current = Path(__file__).resolve().parent
    for _ in range(5):  # Check up to 5 levels up
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        current = current.parent
    # Default to project root assumption
    return Path(__file__).resolve().parent.parent.parent.parent / ".env"


class WorkerConfig(BaseSettings):
    """Worker configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    environment: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    worker_name: str = "jyntrix-worker"

    # Redis configuration (use REDIS_URL directly)
    redis_url: str = Field(default="redis://localhost:6379")

    # ARQ specific settings
    arq_queue_name: str = Field(default="jyntrix:queue")
    arq_max_jobs: int = Field(default=10)
    arq_job_timeout: int = Field(default=300)
    arq_retry_jobs: bool = Field(default=True)
    arq_max_retries: int = Field(default=3)

    # Supabase configuration
    supabase_url: str = Field(...)
    supabase_service_key: SecretStr = Field(...)

    # Qdrant configuration (use URL directly)
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_api_key: SecretStr | None = Field(default=None)
    qdrant_collection: str = Field(default="memories")

    # Embedding model settings
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    embedding_dimension: int = Field(default=384)
    embedding_batch_size: int = Field(default=32)

    # Gemini configuration (matches env var GOOGLE_AI_API_KEY)
    google_ai_api_key: SecretStr = Field(...)
    gemini_model: str = Field(default="gemini-2.5-flash")
    gemini_temperature: float = Field(default=0.3)
    gemini_max_tokens: int = Field(default=2048)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"


@lru_cache
def get_config() -> WorkerConfig:
    """Get cached worker configuration instance."""
    return WorkerConfig()


# Convenience accessor
config = get_config()
