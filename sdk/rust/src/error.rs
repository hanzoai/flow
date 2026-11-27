use std::fmt;

/// Typed HTTP error returned by the Hanzo Flow API.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ApiError {
    pub status: u16,
    pub title: String,
    pub detail: String,
    pub request_id: Option<String>,
}

impl fmt::Display for ApiError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "flow api {} {}", self.status, self.title)?;
        if !self.detail.is_empty() {
            write!(f, ": {}", self.detail)?;
        }
        if let Some(ref req_id) = self.request_id {
            if !req_id.is_empty() {
                write!(f, " (request_id={req_id})")?;
            }
        }
        Ok(())
    }
}

impl std::error::Error for ApiError {}

/// Errors produced by [`crate::FlowClient`].
#[derive(Debug)]
pub enum FlowError {
    /// Non-2xx response returned by the API.
    Api(ApiError),
    /// Network or transport failure.
    Transport(String),
    /// JSON serialization or deserialization failure.
    Json(serde_json::Error),
    /// Caller supplied invalid arguments (e.g. empty workflow ID or name).
    InvalidInput(String),
}

impl fmt::Display for FlowError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            FlowError::Api(err) => write!(f, "{err}"),
            FlowError::Transport(msg) => write!(f, "flow transport error: {msg}"),
            FlowError::Json(err) => write!(f, "flow json error: {err}"),
            FlowError::InvalidInput(msg) => write!(f, "flow invalid input: {msg}"),
        }
    }
}

impl std::error::Error for FlowError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            FlowError::Api(err) => Some(err),
            FlowError::Json(err) => Some(err),
            FlowError::Transport(_) | FlowError::InvalidInput(_) => None,
        }
    }
}

impl From<serde_json::Error> for FlowError {
    fn from(value: serde_json::Error) -> Self {
        FlowError::Json(value)
    }
}
