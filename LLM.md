# LLM.md - Hanzo Flow

## Overview
**Hanzo Flow** is a powerful platform for building and deploying AI-powered agents and workflows. It provides developers with both a visual authoring experience and built-in API and MCP servers.

Internal package name is `flow`; the env prefix is `FLOW_` and nothing else. OSS attribution lives in `NOTICE`.

## Tech Stack
- **Backend**: Python (FastAPI, SQLModel, Alembic)
- **Frontend**: TypeScript/React (Next.js)
- **Package manager**: `uv` (Python), `pnpm` (Node.js)

## Build & Run
```bash
uv sync --all-extras       # Install Python deps
make dev                   # Start dev server
make test                  # Run tests
```

## Package Architecture (2026-03-25)

Three Python packages in a uv workspace:

| Package | PyPI name | Dir | Purpose |
|---------|-----------|-----|---------|
| `flow` | `flow-base` | `src/backend/base/flow/` | Main backend package (454 files) |
| `flow` (root) | `flow` | `src/backend/flow/` | Root package (version only) |
| `lfx` | `lfx` | `src/lfx/src/lfx/` | Lightweight executor, standalone CLI |

### Internal package name: `flow`
- All Python imports use `from flow.xxx` / `import flow.xxx`
- Entry point: `hanzo-flow = "flow.launcher:main"` (root pyproject.toml)
- Entry point: `flow-base = "flow.launcher:main"` (base pyproject.toml)
- Hatch build target: `packages = ["flow"]` (base), `packages = ["src/backend/flow"]` (root)

### PyPI package names
- `flow` -- root package
- `flow-base` -- base package
- `lfx` -- executor package

### Environment variables
- Prefix is `FLOW_` and nothing else (e.g. `FLOW_DATABASE_URL`, `FLOW_LOG_LEVEL`)
- Declared once, via `env_prefix="FLOW_"` in `src/lfx/src/lfx/services/settings/base.py:657`

### Key classes
- `FlowApplication` -- Gunicorn application class (`flow.server`)
- `FlowUvicornWorker` -- Uvicorn worker class (`flow.server`)

## Key Files
- `pyproject.toml` -- Root project config (PyPI name: flow)
- `src/backend/base/pyproject.toml` -- Base package config (PyPI name: flow-base)
- `src/backend/base/flow/launcher.py` -- Main entry point
- `src/backend/base/flow/__main__.py` -- CLI commands (typer app)
- `src/backend/base/flow/main.py` -- FastAPI app factory
- `src/backend/base/flow/alembic/` -- Database migrations
- `Dockerfile` -- Production container
- `Makefile` -- Build automation
