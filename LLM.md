# LLM.md - Hanzo Flow

## Overview
**Hanzo Flow** is a powerful platform for building and deploying AI-powered agents and workflows. It provides developers with both a visual authoring experience and built-in API and MCP servers.

**Upstream**: Langflow (MIT) — https://github.com/langflow-ai/langflow. Internal package name `flow`; canonical env prefix `FLOW_*` (legacy `LANGFLOW_*` retained only for backwards compatibility — do not introduce new `LANGFLOW_*` references).

### Licence
This is a fork, not original work. Langflow's MIT terms govern the whole tree
and ours cannot replace them. NOTICE carries upstream's copyright and permission
notice verbatim, which is what MIT requires us to ship.

LICENSE does not. The upstream line was restored there in 24c1da1168, then
overwritten again by the blanket `langflow`->`flow` rename in 919f7c30e1, which
swept LICENSE along with the docs; f091015e32 repaired NOTICE the same day and
left LICENSE behind. It still reads `Copyright (c) 2024 Hanzo Flow` where
upstream reads `Copyright (c) 2024 Langflow`. That line wants restoring, and
LICENSE and NOTICE want excluding from any future rename sweep.

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
