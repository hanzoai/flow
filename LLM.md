# LLM.md - Hanzo Flow

## Overview
**Hanzo Flow** is a powerful platform for building and deploying AI-powered agents and workflows. It provides developers with both a visual authoring experience and built-in API and MCP servers.

**Upstream**: Hanzo Flow (MIT). Internal package name `flow`; canonical env prefix `FLOW_*` (legacy `FLOW_*` retained only for backwards compatibility — do not introduce new `FLOW_*` references).

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
- The `flow` compat shim package has been removed (was at `src/backend/base/flow/`)
- The `flow` package dir has been renamed to `flow`

### PyPI package names (unchanged)
- `flow` -- root package name in pyproject.toml
- `flow-base` -- base package name in pyproject.toml
- `lfx` -- executor package name

### Environment variables (backwards compat)
- `FLOW_*` env vars are kept for backwards compatibility (e.g. `FLOW_DATABASE_URL`, `FLOW_LOG_LEVEL`)
- These are defined in `lfx/src/lfx/services/settings/base.py` via pydantic-settings

### Key classes
- `FlowApplication` -- Gunicorn application class (`flow.server`)
- `FlowUvicornWorker` -- Uvicorn worker class (`flow.server`)

## Key Files
- `pyproject.toml` -- Root project config (PyPI name: flow)
- `src/backend/base/pyproject.toml` -- Base package config (PyPI name: flow-base)
- `src/backend/base/flow/launcher.py` -- Main entry point (was flow_launcher.py)
- `src/backend/base/flow/__main__.py` -- CLI commands (typer app)
- `src/backend/base/flow/main.py` -- FastAPI app factory
- `src/backend/base/flow/alembic/` -- Database migrations
- `Dockerfile` -- Production container
- `Makefile` -- Build automation
