# Flow → Hanzo Functions (Fission)

Run a Flow (langflow-fork graph) as a Hanzo Function on the live Fission control
plane (`fission` ns, `do-sfo3-hanzo-k8s`). Two compile models; GPU envs host the
Zen-model nodes. Scaffold: `serverless/` (compiler + in-function runner).

## How a Flow runs today

A flow export is a node/edge JSON. Production builds it fresh per request:

```python
graph = Graph.from_payload(flow.data, flow_id, flow_name)      # flow/graph
outputs = await run_flow(inputs=..., graph=graph, user_id=...) # flow/helpers/flow.py:200
```

Functions just needs to do the same inside a function pod.

## Model A — flow-as-function (default, demo path)

The **whole flow** becomes ONE Fission function on a Python env that has
`hanzo-flow`/`lfx` installed.

```
flow.json ──compile──> Fission Function (env=flow-python | flow-gpu)
                        package = { runner.py, flow.json }
                        invoke: POST /v1/functions/{flow} {input_value, tweaks}
                          → runner: Graph.from_payload(flow.json) → run_flow(...) → outputs
```

- **Env**: a custom `flow-python` environment = upstream `python-env` + the
  `hanzo-flow` wheel baked in (build via CI → `ghcr.io/hanzoai/flow-env`). The
  function package is just `runner.py` + the embedded `flow.json`.
- **GPU / Zen models**: if any node is a model node (LLM/embeddings/Zen), compile
  to `flow-gpu` (the `flow-python` image on a GPU env: `fission env create
  --name flow-gpu --image ghcr.io/hanzoai/flow-env-gpu` with GPU resources).
  Inference runs in-pod or, better, the model node calls the LLM gateway
  (`api.hanzo.ai/v1`) so the flow function stays CPU and the gateway owns GPU —
  pick per node (see "GPU placement" below).
- **Billing**: per invocation via the router's `usagemeter` (Provider
  `functions`); GPU-seconds when on `flow-gpu`. Same contract as
  `functions/INTEGRATION.md`.
- **Pros**: one cold start, simple, exact-parity with current execution.
  **Cons**: the whole flow scales as a unit.

This is the demo path: real, minimal, and reuses the existing `run_flow`.

## Model B — node-as-function (opt-in, for scale / isolation / GPU)

Each vertex compiles to its own Fission function; edges become calls. A
coordinator function walks the DAG (topological order, fan-out parallel
branches) invoking node functions through the router.

```
flow.json ──compile──> { coordinator-fn, node-fn × N }
  coordinator: topo-sort vertices → for each, POST /v1/functions/{flow}-{node}
               passing upstream outputs as input; aggregate; return sink output
```

- **GPU placement**: only model/Zen nodes compile to `flow-gpu`; CPU nodes to
  `flow-python`. This is the real win — isolate + scale the expensive node, keep
  the rest cheap and scale-to-zero.
- **Async DAGs**: long branches use Fission message-queue triggers (KEDA/NATS)
  instead of sync calls.
- **Pros**: per-node scaling, GPU isolation, reuse of shared nodes across flows.
  **Cons**: N cold starts, orchestration + payload-passing complexity.

Use B for heavy/parallel/GPU-mixed flows; A everywhere else. One rule:
**a node is its own function only when it needs isolation (GPU) or independent
scale** — otherwise it stays in the flow-as-function (don't fragment for its own
sake).

## GPU placement decision (both models)

| Node | Where it runs | Why |
|------|---------------|-----|
| LLM / Zen model node | call `api.hanzo.ai/v1` (gateway owns GPU + Zen models) | default — no GPU in the flow pod, gateway already pools/scales models |
| Custom model / local weights | `flow-gpu` env (GPU Fission env) | when the node ships its own weights and can't go through the gateway |
| Tools / IO / logic nodes | `flow-python` (CPU, scale-to-zero) | cheap, bursty |

So most flows are CPU functions that call the gateway for inference; only
bring-your-own-model nodes need a GPU env.

## Scaffold (`serverless/`)

- `compiler.py` — `compile_flow(flow_json, runtime, gpu)` → `FunctionSpec`
  (env, package files, entrypoint, fission CLI commands). Model A implemented;
  Model B (`compile_flow_to_dag`) sketched.
- `runner.py` — the in-function entry: load `flow.json`, `Graph.from_payload`,
  `run_flow`, return JSON. This is the function code Model A deploys.
- `__init__.py` — exports.

Deploy (Model A), once `flow-env` is published by CI:

```sh
fission env create --name flow-python --image ghcr.io/hanzoai/flow-env -n fission
python -m serverless.compiler my_flow.json --runtime flow-python   # emits pkg + commands
fission fn create --name my-flow --env flow-python --src ./build/my-flow --entrypoint runner.handler -n fission
curl https://api.hanzo.ai/v1/functions/my-flow -d '{"input_value":"hi"}'
```

## Remaining seams

- Publish `ghcr.io/hanzoai/flow-env` (+ `-gpu`) via CI: `python-env` + the
  `hanzo-flow` wheel. (No local image builds — CI.)
- Coordinator runtime for Model B (topo-walk + MQ-trigger async branches).
- Wire `compile_flow` into the Flow UI ("Deploy as Function" → calls the
  `/v1/functions` management API in `functions/INTEGRATION.md` §3).
