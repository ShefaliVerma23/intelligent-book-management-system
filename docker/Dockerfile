# =============================================================================
# Dockerfile - Intelligent Book Management System
# =============================================================================
# Multi-stage build for optimal image size and security
# Build: docker build -t intelligent-books-api -f docker/Dockerfile .
# Run: docker run -p 8000:8000 --env-file .env intelligent-books-api
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (for better caching)
COPY requirements.txt .

# Create virtual environment and install dependencies
# Note: Uses minimal requirements.txt (no heavy ML deps)
# For local AI models, add requirements-ml.txt
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Production image
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS production

# Labels for container metadata
LABEL maintainer="Book Management System Team" \
      version="1.0.0" \
      description="Intelligent Book Management System API"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Application settings
    APP_HOME=/app \
    APP_USER=appuser \
    APP_GROUP=appgroup

WORKDIR $APP_HOME

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd --gid 1000 $APP_GROUP && \
    useradd --uid 1000 --gid $APP_GROUP --shell /bin/bash --create-home $APP_USER

# Copy application code
COPY --chown=$APP_USER:$APP_GROUP . .

# Create necessary directories
RUN mkdir -p logs && chown -R $APP_USER:$APP_GROUP logs

# Switch to non-root user
USER $APP_USER

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - can be overridden
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# -----------------------------------------------------------------------------
# Stage 3: Development image (optional, for local development)
# -----------------------------------------------------------------------------
FROM production AS development

USER root

# Install development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install development dependencies
RUN pip install pytest pytest-asyncio pytest-cov httpx

USER $APP_USER

# Override command for development (with hot-reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
