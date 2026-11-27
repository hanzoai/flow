//! `hanzo-flow-sdk` — native Rust client for the canonical Hanzo Flow REST API (`/v1/flow/*`).
//!
//! # Example
//!
//! ```no_run
//! use hanzo_flow_sdk::{ClientConfig, CreateWorkflowRequest, FlowClient, RunRequest, WorkflowGraph};
//!
//! # fn main() -> Result<(), Box<dyn std::error::Error>> {
//! let client = FlowClient::new(
//!     ClientConfig::new()
//!         .token(std::env::var("HANZO_API_KEY")?)
//!         .org_id("hanzo"),
//! );
//! let status = client.status()?;
//! println!("reachable={} version={:?}", status.reachable, status.version);
//!
//! let wf = client.create_workflow(&CreateWorkflowRequest {
//!     name: "support-triage".into(),
//!     description: Some("Route incoming tickets".into()),
//!     data: Some(WorkflowGraph::new()),
//! })?;
//! let _run = client.run(&RunRequest::new(wf.id, "Summarize today's tickets"))?;
//! # Ok(())
//! # }
//! ```

mod client;
mod error;
mod types;

pub use client::{ClientConfig, FlowClient, DEFAULT_BASE_URL};
pub use error::{ApiError, FlowError};
pub use types::{
    CreateWorkflowRequest, FlowStatus, GraphEdge, GraphNode, ListOptions, Position, RunRequest,
    RunResponse, RunsResponse, UpdateWorkflowRequest, Workflow, WorkflowGraph, WorkflowList,
    GRAPH_SCHEMA_VERSION,
};
