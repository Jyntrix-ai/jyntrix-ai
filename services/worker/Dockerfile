# Jyntrix AI Memory Architecture Background Worker
# Python 3.11 Production Image

# Build stage for dependencies
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd --gid 1000 worker && \
    useradd --uid 1000 --gid worker --shell /bin/bash --create-home worker

# Install runtime dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Required for some ML libraries
    libgomp1 \
    # For health checks
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=worker:worker . .

# Switch to non-root user
USER worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import asyncio; from src.main import health_check; print(asyncio.run(health_check()))" || exit 1

# Expose metrics port (if using Prometheus metrics)
EXPOSE 9090

# Default command: run ARQ worker
CMD ["arq", "src.main.WorkerSettings"]

# Alternative commands:
# Run with specific concurrency: CMD ["arq", "src.main.WorkerSettings", "--max-jobs", "5"]
# Run with verbose logging: CMD ["arq", "src.main.WorkerSettings", "-v"]
