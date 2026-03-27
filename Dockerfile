# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for Hanzo Flow

################################
# BUILDER
################################
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy all workspace manifests so uv can resolve workspace members.
# README.md files are required by hatchling build-backend.
# src/backend/base/uv.lock is required by the base workspace member.
COPY ./uv.lock /app/uv.lock
COPY ./README.md /app/README.md
COPY ./pyproject.toml /app/pyproject.toml
COPY ./src/backend/base/README.md /app/src/backend/base/README.md
COPY ./src/backend/base/uv.lock /app/src/backend/base/uv.lock
COPY ./src/backend/base/pyproject.toml /app/src/backend/base/pyproject.toml
COPY ./src/lfx/README.md /app/src/lfx/README.md
COPY ./src/lfx/pyproject.toml /app/src/lfx/pyproject.toml

# Create placeholder for root flow package so uv can validate workspace.
# (hatchling needs the package dir to exist; real source is copied after deps install)
RUN mkdir -p /app/src/backend/flow && \
    touch /app/src/backend/flow/__init__.py

# Install dependencies only (no workspace packages yet — source not copied).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --no-editable

# Copy application source code.
COPY ./src /app/src

# Install the workspace packages now that source is available.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

################################
# RUNTIME
################################
FROM python:3.12.12-slim-trixie

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libpq5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r hanzo && useradd -r -g hanzo -d /app/data hanzo

WORKDIR /app

COPY --from=builder --chown=hanzo:hanzo /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=3006

# Copy only what's needed at runtime (not .git, tests, docs, docker/, etc.)
COPY --chown=hanzo:hanzo ./src /app/src
COPY --chown=hanzo:hanzo ./pyproject.toml /app/pyproject.toml
COPY --chown=hanzo:hanzo ./README.md /app/README.md

RUN mkdir -p /app/data /app/logs && chown -R hanzo:hanzo /app/data /app/logs

USER hanzo

EXPOSE 3006

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3006/health || exit 1

CMD ["python", "-m", "langflow", "run", "--host", "0.0.0.0", "--port", "3006"]
