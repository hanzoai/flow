use std::time::Duration;

use serde::de::DeserializeOwned;
use serde::Serialize;

use crate::error::{ApiError, FlowError};
use crate::types::{
    CreateWorkflowRequest, FlowStatus, ListOptions, RunRequest, RunResponse, RunsResponse,
    UpdateWorkflowRequest, Workflow, WorkflowList,
};

/// Canonical Hanzo API origin.
pub const DEFAULT_BASE_URL: &str = "https://api.hanzo.ai";

const DEFAULT_TIMEOUT: Duration = Duration::from_secs(60);

/// Configuration for [`FlowClient`].
#[derive(Debug, Clone)]
pub struct ClientConfig {
    pub base_url: String,
    pub token: Option<String>,
    pub org_id: Option<String>,
    pub timeout: Duration,
}

impl ClientConfig {
    /// Creates a config targeting [`DEFAULT_BASE_URL`] with a 60s timeout.
    pub fn new() -> Self {
        Self {
            base_url: DEFAULT_BASE_URL.to_string(),
            token: None,
            org_id: None,
            timeout: DEFAULT_TIMEOUT,
        }
    }

    /// Overrides the API base URL.
    pub fn base_url(mut self, url: impl Into<String>) -> Self {
        let trimmed = url.into();
        let trimmed = trimmed.trim().trim_end_matches('/');
        if !trimmed.is_empty() {
            self.base_url = trimmed.to_string();
        }
        self
    }

    /// Sets the Bearer token sent in `Authorization: Bearer <token>`.
    pub fn token(mut self, token: impl Into<String>) -> Self {
        let t = token.into();
        let t = t.trim();
        self.token = if t.is_empty() {
            None
        } else {
            Some(t.to_string())
        };
        self
    }

    /// Sets the active organization slug sent in `X-Org-Id`.
    pub fn org_id(mut self, org_id: impl Into<String>) -> Self {
        let o = org_id.into();
        let o = o.trim();
        self.org_id = if o.is_empty() {
            None
        } else {
            Some(o.to_string())
        };
        self
    }

    /// Sets the overall per-request timeout.
    pub fn timeout(mut self, timeout: Duration) -> Self {
        self.timeout = timeout;
        self
    }
}

impl Default for ClientConfig {
    fn default() -> Self {
        Self::new()
    }
}

/// Synchronous HTTP client for the canonical Hanzo Flow REST API (`/v1/flow/*`).
#[derive(Debug, Clone)]
pub struct FlowClient {
    config: ClientConfig,
    agent: ureq::Agent,
}

impl FlowClient {
    /// Constructs a new [`FlowClient`] from `config`.
    pub fn new(config: ClientConfig) -> Self {
        let agent = ureq::AgentBuilder::new().timeout(config.timeout).build();
        Self { config, agent }
    }

    /// Reports service reachability and version via `GET /v1/flow/status`.
    pub fn status(&self) -> Result<FlowStatus, FlowError> {
        self.request_json("GET", "/v1/flow/status", &[], Option::<&()>::None)
    }

    /// Lists org-scoped workflows via `GET /v1/flow/workflows`.
    pub fn list_workflows(&self, opts: &ListOptions) -> Result<WorkflowList, FlowError> {
        let mut query: Vec<(&str, String)> = Vec::new();
        if let Some(page) = opts.page {
            query.push(("page", page.to_string()));
        }
        if let Some(size) = opts.size {
            query.push(("size", size.to_string()));
        }
        let borrowed: Vec<(&str, &str)> = query.iter().map(|(k, v)| (*k, v.as_str())).collect();
        self.request_json("GET", "/v1/flow/workflows", &borrowed, Option::<&()>::None)
    }

    /// Fetches one workflow by ID via `GET /v1/flow/workflows/{id}`.
    pub fn get_workflow(&self, id: &str) -> Result<Workflow, FlowError> {
        let seg = encode_segment(id, "workflow id")?;
        self.request_json(
            "GET",
            &format!("/v1/flow/workflows/{seg}"),
            &[],
            Option::<&()>::None,
        )
    }

    /// Creates a workflow in the caller's org via `POST /v1/flow/workflows`.
    pub fn create_workflow(&self, req: &CreateWorkflowRequest) -> Result<Workflow, FlowError> {
        if req.name.trim().is_empty() {
            return Err(FlowError::InvalidInput("workflow name is required".into()));
        }
        self.request_json("POST", "/v1/flow/workflows", &[], Some(req))
    }

    /// Patches a workflow via `PATCH /v1/flow/workflows/{id}`.
    pub fn update_workflow(
        &self,
        id: &str,
        req: &UpdateWorkflowRequest,
    ) -> Result<Workflow, FlowError> {
        let seg = encode_segment(id, "workflow id")?;
        self.request_json(
            "PATCH",
            &format!("/v1/flow/workflows/{seg}"),
            &[],
            Some(req),
        )
    }

    /// Deletes a workflow and its runs via `DELETE /v1/flow/workflows/{id}`.
    pub fn delete_workflow(&self, id: &str) -> Result<(), FlowError> {
        let seg = encode_segment(id, "workflow id")?;
        let _ = self.send_raw(
            "DELETE",
            &format!("/v1/flow/workflows/{seg}"),
            &[],
            Option::<&()>::None,
        )?;
        Ok(())
    }

    /// Executes a workflow synchronously via `POST /v1/flow/runs`.
    pub fn run(&self, req: &RunRequest) -> Result<RunResponse, FlowError> {
        if req.workflow.trim().is_empty() {
            return Err(FlowError::InvalidInput("workflow id is required".into()));
        }
        self.request_json("POST", "/v1/flow/runs", &[], Some(req))
    }

    /// Lists recorded runs for a workflow via `GET /v1/flow/runs?workflow={id}`.
    pub fn list_runs(&self, workflow_id: &str) -> Result<RunsResponse, FlowError> {
        let wf = workflow_id.trim();
        if wf.is_empty() {
            return Err(FlowError::InvalidInput("workflow id is required".into()));
        }
        self.request_json(
            "GET",
            "/v1/flow/runs",
            &[("workflow", wf)],
            Option::<&()>::None,
        )
    }

    fn request_json<B: Serialize, T: DeserializeOwned>(
        &self,
        method: &str,
        path: &str,
        query: &[(&str, &str)],
        body: Option<&B>,
    ) -> Result<T, FlowError> {
        let text = self.send_raw(method, path, query, body)?;
        let parsed = serde_json::from_str(&text)?;
        Ok(parsed)
    }

    fn send_raw<B: Serialize>(
        &self,
        method: &str,
        path: &str,
        query: &[(&str, &str)],
        body: Option<&B>,
    ) -> Result<String, FlowError> {
        let url = format!("{}{}", self.config.base_url, path);
        let mut req = self
            .agent
            .request(method, &url)
            .set("Accept", "application/json");
        for (k, v) in query {
            req = req.query(k, v);
        }
        if let Some(ref token) = self.config.token {
            req = req.set("Authorization", &format!("Bearer {token}"));
        }
        if let Some(ref org_id) = self.config.org_id {
            req = req.set("X-Org-Id", org_id);
        }

        let outcome = if let Some(payload) = body {
            let encoded = serde_json::to_string(payload)?;
            req.set("Content-Type", "application/json")
                .send_string(&encoded)
        } else {
            req.call()
        };

        match outcome {
            Ok(resp) => resp
                .into_string()
                .map_err(|e| FlowError::Transport(e.to_string())),
            Err(ureq::Error::Status(status, resp)) => {
                Err(FlowError::Api(decode_api_error(status, resp)))
            }
            Err(ureq::Error::Transport(err)) => Err(FlowError::Transport(err.to_string())),
        }
    }
}

fn encode_segment(raw: &str, label: &str) -> Result<String, FlowError> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Err(FlowError::InvalidInput(format!("{label} is required")));
    }
    let mut out = String::with_capacity(trimmed.len());
    for byte in trimmed.bytes() {
        let unreserved = byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_' | b'.' | b'~');
        if unreserved {
            out.push(byte as char);
        } else {
            out.push_str(&format!("%{byte:02X}"));
        }
    }
    Ok(out)
}

fn decode_api_error(status: u16, resp: ureq::Response) -> ApiError {
    let header_req_id = resp.header("X-Request-Id").map(str::to_string);
    let status_text = resp.status_text().to_string();
    let body = resp.into_string().unwrap_or_default();

    let mut api_err = ApiError {
        status,
        title: if status_text.is_empty() {
            format!("HTTP {status}")
        } else {
            status_text
        },
        detail: String::new(),
        request_id: header_req_id,
    };

    if let Ok(val) = serde_json::from_str::<serde_json::Value>(&body) {
        if let Some(obj) = val.as_object() {
            if let Some(st) = obj.get("status").and_then(serde_json::Value::as_u64) {
                if let Ok(code) = u16::try_from(st) {
                    api_err.status = code;
                }
            }
            if let Some(title) = obj.get("title").and_then(serde_json::Value::as_str) {
                if !title.is_empty() {
                    api_err.title = title.to_string();
                }
            }
            if api_err.request_id.is_none() {
                if let Some(req_id) = obj.get("request_id").and_then(serde_json::Value::as_str) {
                    if !req_id.is_empty() {
                        api_err.request_id = Some(req_id.to_string());
                    }
                }
            }
            for key in ["detail", "message", "error"] {
                if let Some(v) = obj.get(key) {
                    if let Some(s) = v.as_str() {
                        api_err.detail = s.to_string();
                    } else if !v.is_null() {
                        api_err.detail = v.to_string();
                    }
                    if !api_err.detail.is_empty() {
                        break;
                    }
                }
            }
        }
    }

    if api_err.detail.is_empty() {
        api_err.detail = body.trim().to_string();
    }
    api_err
}
