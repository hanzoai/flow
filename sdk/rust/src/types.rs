use std::collections::BTreeMap;

use serde::{Deserialize, Deserializer, Serialize};
use serde_json::Value;

/// Canonical portable workflow graph schema identifier.
pub const GRAPH_SCHEMA_VERSION: &str = "hanzo.flow/v1";

fn default_schema() -> String {
    GRAPH_SCHEMA_VERSION.to_string()
}

/// Health and version payload returned by `GET /v1/flow/status`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FlowStatus {
    pub reachable: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub version: Option<String>,
}

/// Canvas coordinates for a [`GraphNode`].
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Position {
    pub x: f64,
    pub y: f64,
}

/// A node inside a `hanzo.flow/v1` [`WorkflowGraph`].
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GraphNode {
    pub id: String,
    #[serde(default, rename = "type", skip_serializing_if = "String::is_empty")]
    pub node_type: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub position: Option<Position>,
}

/// A directed edge inside a `hanzo.flow/v1` [`WorkflowGraph`].
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GraphEdge {
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub id: String,
    pub source: String,
    #[serde(
        default,
        rename = "sourceHandle",
        skip_serializing_if = "Option::is_none"
    )]
    pub source_handle: Option<String>,
    pub target: String,
    #[serde(
        default,
        rename = "targetHandle",
        skip_serializing_if = "Option::is_none"
    )]
    pub target_handle: Option<String>,
}

/// Portable `hanzo.flow/v1` workflow graph document.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WorkflowGraph {
    #[serde(default = "default_schema")]
    pub schema: String,
    #[serde(default)]
    pub nodes: Vec<GraphNode>,
    #[serde(default)]
    pub edges: Vec<GraphEdge>,
}

impl WorkflowGraph {
    /// Creates an empty `hanzo.flow/v1` graph.
    pub fn new() -> Self {
        Self {
            schema: default_schema(),
            nodes: Vec::new(),
            edges: Vec::new(),
        }
    }
}

impl Default for WorkflowGraph {
    fn default() -> Self {
        Self::new()
    }
}

/// Workflow record returned by `/v1/flow/workflows`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Workflow {
    pub id: String,
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub data: Option<WorkflowGraph>,
    #[serde(default)]
    pub locked: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub folder_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub endpoint_name: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tags: Option<Vec<String>>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub updated_at: Option<String>,
}

/// Pagination options for `GET /v1/flow/workflows`.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct ListOptions {
    pub page: Option<u32>,
    pub size: Option<u32>,
}

/// Workflow list returned by `GET /v1/flow/workflows`.
///
/// Decodes both paginated objects (`{"flows": [...], "total": ...}` or `{"items": [...]}`)
/// and plain JSON arrays (`[...]`).
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct WorkflowList {
    pub workflows: Vec<Workflow>,
    pub total: usize,
    pub page: Option<u32>,
    pub size: Option<u32>,
    pub pages: Option<u32>,
}

impl<'de> Deserialize<'de> for WorkflowList {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        #[derive(Deserialize)]
        #[serde(untagged)]
        enum Raw {
            Array(Vec<Workflow>),
            Envelope {
                #[serde(default)]
                flows: Option<Vec<Workflow>>,
                #[serde(default)]
                items: Option<Vec<Workflow>>,
                #[serde(default)]
                total: Option<usize>,
                #[serde(default)]
                page: Option<u32>,
                #[serde(default)]
                size: Option<u32>,
                #[serde(default)]
                pages: Option<u32>,
            },
        }
        match Raw::deserialize(deserializer)? {
            Raw::Array(workflows) => {
                let total = workflows.len();
                Ok(Self {
                    workflows,
                    total,
                    page: None,
                    size: None,
                    pages: None,
                })
            }
            Raw::Envelope {
                flows,
                items,
                total,
                page,
                size,
                pages,
            } => {
                let workflows = flows.or(items).unwrap_or_default();
                let total = total.unwrap_or(workflows.len());
                Ok(Self {
                    workflows,
                    total,
                    page,
                    size,
                    pages,
                })
            }
        }
    }
}

/// Request body for `POST /v1/flow/workflows`.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct CreateWorkflowRequest {
    pub name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<WorkflowGraph>,
}

/// Partial patch body for `PATCH /v1/flow/workflows/{id}`.
#[derive(Debug, Clone, Default, PartialEq, Serialize)]
pub struct UpdateWorkflowRequest {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<WorkflowGraph>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub locked: Option<bool>,
}

/// Request body for `POST /v1/flow/runs`.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct RunRequest {
    pub workflow: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub input: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tweaks: Option<Value>,
}

impl RunRequest {
    /// Creates a synchronous run request for `workflow` with `input`.
    pub fn new(workflow: impl Into<String>, input: impl Into<String>) -> Self {
        Self {
            workflow: workflow.into(),
            input: input.into(),
            session: None,
            tweaks: None,
        }
    }
}

/// Response of `POST /v1/flow/runs`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RunResponse {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
    #[serde(default)]
    pub outputs: Vec<Value>,
}

/// Response of `GET /v1/flow/runs?workflow={id}`.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct RunsResponse {
    pub vertex_builds: BTreeMap<String, Value>,
    pub runs: Vec<Value>,
    pub raw: Value,
}

impl<'de> Deserialize<'de> for RunsResponse {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let raw = Value::deserialize(deserializer)?;
        let mut vertex_builds = BTreeMap::new();
        let mut runs = Vec::new();
        match &raw {
            Value::Array(items) => {
                runs.clone_from(items);
            }
            Value::Object(map) => {
                if let Some(Value::Object(vb)) = map.get("vertex_builds") {
                    for (k, v) in vb {
                        vertex_builds.insert(k.clone(), v.clone());
                    }
                }
                if let Some(Value::Array(items)) = map.get("runs") {
                    runs.clone_from(items);
                }
            }
            _ => {}
        }
        Ok(Self {
            vertex_builds,
            runs,
            raw,
        })
    }
}
