"""FastAPI application entry point."""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings
from src.routers import analytics, auth, chat, health, memory, profile

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and adding request IDs."""

    async def dispatch(self, request: Request, call_next):
        """Process the request and log details."""
        request_id = str(uuid4())
        request.state.request_id = request_id

        start_time = time.time()

        # Log request
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"

            logger.info(
                f"Response {request_id}: {response.status_code} "
                f"in {process_time:.4f}s"
            )

            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Error {request_id}: {str(e)} in {process_time:.4f}s"
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""

    def __init__(self, app, requests_per_window: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.request_counts: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        """Check rate limit before processing request."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/health", "/"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Clean old entries and count recent requests
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                t for t in self.request_counts[client_ip]
                if current_time - t < self.window_seconds
            ]
        else:
            self.request_counts[client_ip] = []

        # Check rate limit
        if len(self.request_counts[client_ip]) >= self.requests_per_window:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": self.window_seconds,
                },
            )

        # Record this request
        self.request_counts[client_ip].append(current_time)

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize connections (lazy loading, actual connections happen on first use)
    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Flush remaining analytics data
    if settings.analytics_enabled:
        try:
            from src.analytics.emitter import _emitter
            if _emitter:
                logger.info("Flushing remaining analytics data...")
                await _emitter.shutdown()
                logger.info("Analytics flush complete")
        except Exception as e:
            logger.error(f"Error flushing analytics: {e}")

    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI Memory Architecture API for personalized AI interactions",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Add custom middlewares
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window,
    )

    # Register exception handlers
    register_exception_handlers(app)

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
    app.include_router(memory.router, prefix="/api/memories", tags=["Memory"])
    app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors."""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": errors,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Handle value errors."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(PermissionError)
    async def permission_error_handler(
        request: Request, exc: PermissionError
    ) -> JSONResponse:
        """Handle permission errors."""
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc)},
        )

    @app.exception_handler(FileNotFoundError)
    async def not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
        """Handle not found errors."""
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all other exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception(f"Unhandled exception in request {request_id}: {exc}")

        # Don't expose internal errors in production
        if settings.is_production:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "An internal error occurred",
                    "request_id": request_id,
                },
            )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "request_id": request_id,
            },
        )


# Create the application instance
app = create_app()


@app.get("/", include_in_schema=False)
async def root() -> dict[str, Any]:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
        "docs": "/docs" if settings.is_development else None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        workers=1 if settings.is_development else settings.workers,
        log_level=settings.log_level.lower(),
    )
