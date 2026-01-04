"""Health check endpoints."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Current environment")
    services: dict[str, Any] = Field(default_factory=dict)


class ServiceHealth(BaseModel):
    """Individual service health status."""

    status: str
    latency_ms: float | None = None
    message: str | None = None


@router.get(
    "/health",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check the health status of the API and its dependencies",
)
async def health_check() -> HealthStatus:
    """Basic health check endpoint."""
    return HealthStatus(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
        services={
            "api": {"status": "healthy"},
        },
    )


@router.get(
    "/health/detailed",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Detailed Health Check",
    description="Check health of all dependent services",
)
async def detailed_health_check() -> HealthStatus:
    """Detailed health check with all service statuses."""
    services: dict[str, Any] = {}
    overall_status = "healthy"

    # Check Supabase
    try:
        from src.db.supabase import get_supabase_client

        client = get_supabase_client()
        # Simple check - if we can create client, connection params are valid
        services["supabase"] = {
            "status": "healthy",
            "message": "Connection configured",
        }
    except Exception as e:
        logger.error(f"Supabase health check failed: {e}")
        services["supabase"] = {
            "status": "unhealthy",
            "message": str(e),
        }
        overall_status = "degraded"

    # Check Qdrant
    try:
        from src.db.qdrant import get_qdrant_client

        client = get_qdrant_client()
        # Try to get collections to verify connection
        import time
        start = time.time()
        collections = client.get_collections()
        latency = (time.time() - start) * 1000

        services["qdrant"] = {
            "status": "healthy",
            "latency_ms": round(latency, 2),
            "collections": len(collections.collections),
        }
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        services["qdrant"] = {
            "status": "unhealthy",
            "message": str(e),
        }
        overall_status = "degraded"

    # Check Redis
    try:
        from src.db.redis import get_redis_client

        import time
        start = time.time()
        client = await get_redis_client()
        await client.ping()
        latency = (time.time() - start) * 1000

        services["redis"] = {
            "status": "healthy",
            "latency_ms": round(latency, 2),
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        services["redis"] = {
            "status": "unhealthy",
            "message": str(e),
        }
        overall_status = "degraded"

    # Check embedding model availability
    try:
        from src.core.embeddings import get_embedding_service

        embedder = get_embedding_service()
        services["embeddings"] = {
            "status": "healthy",
            "model": settings.embedding_model,
            "dimensions": settings.embedding_dimensions,
        }
    except Exception as e:
        logger.error(f"Embedding service health check failed: {e}")
        services["embeddings"] = {
            "status": "unhealthy",
            "message": str(e),
        }
        overall_status = "degraded"

    return HealthStatus(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        services=services,
    )


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness Check",
    description="Check if the service is ready to accept traffic",
)
async def readiness_check() -> dict[str, Any]:
    """Kubernetes-style readiness probe."""
    # For now, always ready if the service is running
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness Check",
    description="Check if the service is alive",
)
async def liveness_check() -> dict[str, Any]:
    """Kubernetes-style liveness probe."""
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
    }
