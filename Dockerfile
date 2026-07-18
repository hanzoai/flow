# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for Hanzo Flow.
#
# ONE image, ONE origin: the Go `flowweb` front door (:8080) serves the embedded
# UI + landing and reverse-proxies /api to the Python flow backend (:7860, on
# loopback). No separate flow-site landing, no second app host. See
# core/cmd/flowweb. Mirrors hanzoai/world + hanzoai/cloud's embedded-SPA pattern.

################################
# FRONTEND — build the Vite UI
################################
FROM node:20-slim AS frontend

WORKDIR /fe
COPY ./src/frontend/package.json ./src/frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY ./src/frontend/ ./
RUN npm run build          # → /fe/build (Vite outDir)

################################
# GOWEB — embed the UI into flowweb
################################
FROM golang:1.23-bookworm AS goweb

WORKDIR /src
COPY ./core/ ./core/
# Overwrite the committed landing placeholder with the real Vite bundle, then
# go:embed it into a static, CGO-free binary.
COPY --from=frontend /fe/build/ ./core/cmd/flowweb/frontend/
WORKDIR /src/core
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /flowweb ./cmd/flowweb

################################
# BUILDER — Python deps
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
# --extra postgresql: production uses PostgreSQL (psycopg driver required)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --no-editable --extra postgresql

# Copy application source code.
COPY ./src /app/src

# Install the workspace packages now that source is available.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --extra postgresql

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
# The Go front door (embedded UI + landing).
COPY --from=goweb --chown=hanzo:hanzo /flowweb /app/flowweb

ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Python backend on loopback; flowweb fronts it on the public port.
ENV PORT=7860
ENV FLOW_WEB_PORT=8080
ENV FLOW_BACKEND_URL=http://127.0.0.1:7860

# Copy only what's needed at runtime (not .git, tests, docs, docker/, etc.)
COPY --chown=hanzo:hanzo ./src /app/src
COPY --chown=hanzo:hanzo ./pyproject.toml /app/pyproject.toml
COPY --chown=hanzo:hanzo ./README.md /app/README.md

RUN mkdir -p /app/data /app/logs && chown -R hanzo:hanzo /app/data /app/logs

USER hanzo

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Python flow backend (API only) on loopback; exec flowweb as PID 1's foreground
# so the container restarts if the front door dies. flowweb serves the embedded UI
# + landing and proxies /api → 127.0.0.1:7860.
CMD ["sh", "-c", "python -m flow run --host 127.0.0.1 --port 7860 --backend-only & exec /app/flowweb"]
