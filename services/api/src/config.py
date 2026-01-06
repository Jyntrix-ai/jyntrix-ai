"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
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


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Jyntrix AI Memory API"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:5173"])
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = Field(default=["*"])
    cors_allow_headers: list[str] = Field(default=["*"])

    # Supabase
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anonymous key")
    supabase_service_key: str = Field(..., description="Supabase service role key")

    # Qdrant
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "memories"
    qdrant_vector_size: int = 384  # all-MiniLM-L6-v2 dimensions

    # Redis
    redis_url: str = Field(default="redis://localhost:6379")
    redis_password: str | None = None
    redis_db: int = 0
    redis_cache_ttl: int = 3600  # 1 hour

    # Google Gemini
    google_ai_api_key: str = Field(..., description="Google AI API key")
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_tokens: int = 4096
    gemini_temperature: float = 0.7

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimensions: int = 384

    # Token Budget (reduced ~40% for faster LLM processing)
    max_context_tokens: int = 5000      # was 8000
    profile_memory_tokens: int = 600    # was 1000
    semantic_memory_tokens: int = 1500  # was 2500
    episodic_memory_tokens: int = 1500  # was 2500
    procedural_memory_tokens: int = 400 # was 1000
    entity_memory_tokens: int = 300     # was 500
    conversation_history_tokens: int = 300  # was 500

    # Hybrid Ranking Weights
    keyword_match_weight: float = 0.35
    vector_similarity_weight: float = 0.25
    reliability_weight: float = 0.20
    recency_weight: float = 0.15
    frequency_weight: float = 0.05

    # JWT Settings (for token validation)
    jwt_algorithm: str = "HS256"
    jwt_secret_key: str = Field(default="", description="JWT secret for validation")

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # ARQ Background Tasks
    arq_redis_url: str = Field(default="redis://localhost:6379/1")

    # Analytics
    analytics_enabled: bool = Field(default=True, description="Enable analytics collection")
    analytics_buffer_size: int = Field(default=10, description="Max records to buffer before flush")
    analytics_flush_interval: int = Field(default=10, description="Seconds between auto-flushes")
    analytics_retention_days: int = Field(default=90, description="Days to retain analytics data")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
