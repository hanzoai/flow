# Multi-stage Dockerfile for Hanzo Flow
# This Dockerfile creates a production-ready image for the Hanzo Flow visual workflow builder

# Build stage
FROM python:3.12-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy all workspace manifests so uv can resolve workspace members
COPY pyproject.toml uv.lock ./
COPY src/backend/base/pyproject.toml ./src/backend/base/
COPY src/lfx/pyproject.toml ./src/lfx/

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r hanzo && useradd -r -g hanzo hanzo

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=hanzo:hanzo . .

# Set environment variables
ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=3006

# Create necessary directories
RUN mkdir -p /app/data /app/logs && chown -R hanzo:hanzo /app/data /app/logs

# Switch to non-root user
USER hanzo

# Expose port
EXPOSE 3006

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3006/health || exit 1

# Start the application
CMD ["hanzoflow", "run", "--host", "0.0.0.0", "--port", "3006"]