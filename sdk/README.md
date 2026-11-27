# Hanzo Flow SDKs

Native SDKs for the canonical **Hanzo Flow** REST API (`https://api.hanzo.ai`, `/v1/flow/*`, `Authorization: Bearer <token>`, `X-Org-Id`) plus embedded `flow-core` DAG engines.

| Language | Package / Target | Path | Dependencies | Surface |
|----------|------------------|------|--------------|---------|
| **Python** | `hanzo-flow-sdk` (`flow_sdk`) | [`src/sdk`](../src/sdk/README.md) | `httpx`, `pydantic` | `/v1/flow/*` + direct `/v1/flows/*`, `/v1/run/*`, SSE streaming, `pytest` plugin |
| **Go** | `github.com/hanzoai/flow/sdk/go` | [`sdk/go`](./go/README.md) | Go stdlib only (`0` external deps) | `/v1/flow/*` + `hanzo.flow/v1` `WorkflowGraph` |
| **Rust** | `hanzo-flow-sdk` | [`sdk/rust`](./rust/README.md) | `serde`, `serde_json`, `ureq` | `/v1/flow/*` + `hanzo.flow/v1` `WorkflowGraph` |
| **C++20** | `hanzo::flow` (`hanzo_flow_core`, `hanzo_flow_sdk`) | [`sdk/cpp`](./cpp/README.md) | `libcurl` (SDK); `0` deps (core) | 1:1 `flow-core` DAG engine + `/v1/flow/*` REST client |

## Canonical `/v1/flow/*` Operations

Every SDK implements the same canonical surface against `https://api.hanzo.ai`:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/v1/flow/status` | Service reachability & version |
| `GET` | `/v1/flow/workflows` | List org-scoped workflows (`page`, `size`) |
| `POST` | `/v1/flow/workflows` | Create workflow (`name`, `description`, `hanzo.flow/v1` `data`) |
| `GET` | `/v1/flow/workflows/{id}` | Fetch workflow record & graph |
| `PATCH` | `/v1/flow/workflows/{id}` | Partial update (`name`, `description`, `data`, `locked`) |
| `DELETE` | `/v1/flow/workflows/{id}` | Delete workflow and its runs |
| `POST` | `/v1/flow/runs` | Execute workflow synchronously |
| `GET` | `/v1/flow/runs?workflow={id}` | List recorded component runs |

## Embedded `flow-core` DAG Engine Parity

The step-DAG scheduler is mirrored 1:1 across Go ([`core/`](../core)), Rust ([`core-rs/`](../core-rs)), and C++20 ([`sdk/cpp/include/hanzo/flow/core.hpp`](./cpp/include/hanzo/flow/core.hpp)): typed ports with `*` wildcard, zero-copy value passing, deterministic Kahn topological validation, and pluggable `Mode` (`InProcess` / `GpuResident` / `Durable`) backends.
