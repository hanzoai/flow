# hanzo-flow-sdk

Official Python SDK for the **Hanzo Flow** REST API (`https://api.hanzo.ai`).

Supports both:
- **Canonical Hanzo Cloud API (`/v1/flow/*`)** using Hanzo IAM Bearer tokens (`Authorization: Bearer <token>`) and org scoping (`X-Org-Id`).
- **Direct Flow backend API (`/v1/flows/*`, `/v1/run/*`, `/v1/projects/*`)** including SSE streaming, background jobs, git-friendly push/pull normalization, and the `pytest` plugin.

## Installation

```bash
uv add hanzo-flow-sdk
# or
pip install hanzo-flow-sdk
```

With the `pytest` integration-testing plugin:

```bash
uv add "hanzo-flow-sdk[testing]"
```

## Quickstart — Canonical `/v1/flow/*` API

```python
import os
from flow_sdk import Client, WorkflowGraph

with Client(
    base_url="https://api.hanzo.ai",
    token=os.environ["HANZO_API_KEY"],
    org_id="hanzo",
) as client:
    # Check service health & version
    status = client.flow_status()
    print(status.reachable, status.version)

    # Create a workflow with a hanzo.flow/v1 graph
    graph = WorkflowGraph(nodes=[], edges=[])
    wf = client.create_workflow(
        "support-triage",
        description="Route incoming support tickets",
        data=graph,
    )
    wf_id = wf["id"]

    # List, fetch, and patch workflows
    workflows = client.list_workflows(page=1, size=25)
    fetched = client.get_workflow(wf_id)
    client.update_workflow(wf_id, description="Route tickets to queues", locked=False)

    # Execute synchronously & inspect recorded runs
    result = client.run_workflow(wf_id, input_value="Summarize today's tickets")
    runs = client.list_runs(wf_id)

    # Delete workflow
    client.delete_workflow(wf_id)
```

### Async Client

```python
import os
from flow_sdk import AsyncClient

async with AsyncClient(
    base_url="https://api.hanzo.ai",
    token=os.environ["HANZO_API_KEY"],
    org_id="hanzo",
) as client:
    status = await client.flow_status()
    workflows = await client.list_workflows(page=1, size=25)
```

## Direct Flow Backend & Streaming

```python
from flow_sdk import Client

with Client("https://flow.hanzo.ai", token="...", org_id="hanzo") as client:
    # Synchronous run
    res = client.run("my-flow-endpoint", input_value="Hello!")
    print(res.first_text_output())

    # Streaming run
    for chunk in client.stream("my-flow-endpoint", input_value="Stream this"):
        if chunk.is_token and chunk.text:
            print(chunk.text, end="", flush=True)

    # Git-friendly pull / push
    client.pull("00000000-0000-0000-0000-000000000001", output="flows/my-flow.json")
    flow, created = client.push("flows/my-flow.json")
```

## Environments Configuration (`flow-environments.toml`)

Copy [`flow-environments.toml.example`](./flow-environments.toml.example) to `flow-environments.toml` in your project root or `~/.config/flow/environments.toml`:

```toml
[environments.production]
url = "https://api.hanzo.ai"
token_env = "HANZO_API_KEY"
org_id = "hanzo"

[defaults]
environment = "production"
```

Then construct a client directly from the named environment:

```python
from flow_sdk import get_client

with get_client("production") as client:
    print(client.flow_status())
```

## Other Languages

See [`sdk/README.md`](../../sdk/README.md) for the full native SDK matrix:
- **Python**: `src/sdk` (`hanzo-flow-sdk`)
- **Go**: `sdk/go` (`github.com/hanzoai/flow/sdk/go`)
- **Rust**: `sdk/rust` (`hanzo-flow-sdk`)
- **C++20**: `sdk/cpp` (`hanzo::flow`)

## License

MIT
