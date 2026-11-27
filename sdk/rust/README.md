# Hanzo Flow Rust SDK (`hanzo-flow-sdk`)

Minimal, native Rust SDK for the canonical **Hanzo Flow** REST API (`/v1/flow/*`).

## Usage

```toml
[dependencies]
hanzo-flow-sdk = "0.1"
```

```rust
use hanzo_flow_sdk::{ClientConfig, CreateWorkflowRequest, FlowClient, RunRequest, WorkflowGraph};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = FlowClient::new(
        ClientConfig::new()
            .token(std::env::var("HANZO_API_KEY")?)
            .org_id("hanzo"),
    );

    let st = client.status()?;
    println!("reachable={} version={:?}", st.reachable, st.version);

    let wf = client.create_workflow(&CreateWorkflowRequest {
        name: "support-triage".into(),
        description: Some("Route incoming tickets".into()),
        data: Some(WorkflowGraph::new()),
    })?;

    let res = client.run(&RunRequest::new(wf.id, "Summarize today's tickets"))?;
    println!("session={:?}", res.session_id);
    Ok(())
}
```

## Test

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
```
