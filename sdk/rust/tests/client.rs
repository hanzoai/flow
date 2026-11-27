use std::collections::HashMap;
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::{Arc, Mutex};
use std::thread;

use hanzo_flow_sdk::{
    ClientConfig, CreateWorkflowRequest, FlowClient, FlowError, GraphEdge, GraphNode, ListOptions,
    RunRequest, UpdateWorkflowRequest, WorkflowGraph, DEFAULT_BASE_URL, GRAPH_SCHEMA_VERSION,
};
use serde_json::json;

const TEST_WF_ID: &str = "8f14e45f-ceea-467a-8a3b-111111111111";
const TEST_TOKEN: &str = "hz-test-token";
const TEST_ORG: &str = "hanzo";

struct CapturedReq {
    method: String,
    target: String,
    headers: HashMap<String, String>,
    body: String,
}

struct MockResp {
    status: u16,
    reason: &'static str,
    headers: Vec<(&'static str, &'static str)>,
    body: String,
}

fn spawn_mock_server<F>(expected_requests: usize, handler: F) -> (String, thread::JoinHandle<()>)
where
    F: Fn(&CapturedReq) -> MockResp + Send + 'static,
{
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind loopback");
    let addr = listener.local_addr().expect("local addr");
    let handle = thread::spawn(move || {
        for _ in 0..expected_requests {
            let (stream, _) = listener.accept().expect("accept");
            handle_conn(stream, &handler);
        }
    });
    (format!("http://{addr}"), handle)
}

fn handle_conn<F>(mut stream: TcpStream, handler: &F)
where
    F: Fn(&CapturedReq) -> MockResp,
{
    let mut reader = BufReader::new(stream.try_clone().expect("clone stream"));
    let mut request_line = String::new();
    reader.read_line(&mut request_line).expect("request line");
    let parts: Vec<&str> = request_line.split_whitespace().collect();
    let method = parts[0].to_string();
    let target = parts[1].to_string();

    let mut headers = HashMap::new();
    let mut content_len: usize = 0;
    loop {
        let mut line = String::new();
        reader.read_line(&mut line).expect("header line");
        let trimmed = line.trim_end_matches(['\r', '\n']);
        if trimmed.is_empty() {
            break;
        }
        if let Some((k, v)) = trimmed.split_once(':') {
            let key = k.trim().to_ascii_lowercase();
            let val = v.trim().to_string();
            if key == "content-length" {
                content_len = val.parse().unwrap_or(0);
            }
            headers.insert(key, val);
        }
    }

    let mut body_buf = vec![0u8; content_len];
    if content_len > 0 {
        reader.read_exact(&mut body_buf).expect("body");
    }
    let body = String::from_utf8(body_buf).expect("utf8 body");

    let req = CapturedReq {
        method,
        target,
        headers,
        body,
    };
    let resp = handler(&req);

    let mut raw = format!(
        "HTTP/1.1 {} {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n",
        resp.status,
        resp.reason,
        resp.body.len()
    );
    for (k, v) in resp.headers {
        raw.push_str(&format!("{k}: {v}\r\n"));
    }
    raw.push_str("\r\n");
    raw.push_str(&resp.body);
    stream.write_all(raw.as_bytes()).expect("write response");
    let _ = stream.flush();
}

#[test]
fn config_defaults_to_canonical_origin() {
    let cfg = ClientConfig::new();
    assert_eq!(cfg.base_url, DEFAULT_BASE_URL);
    assert!(cfg.token.is_none());
    assert!(cfg.org_id.is_none());
}

#[test]
fn canonical_flow_endpoints_roundtrip() {
    let seen: Arc<Mutex<Vec<String>>> = Arc::new(Mutex::new(Vec::new()));
    let seen_srv = Arc::clone(&seen);

    let (base_url, handle) = spawn_mock_server(8, move |req| {
        assert_eq!(
            req.headers.get("authorization").map(String::as_str),
            Some("Bearer hz-test-token")
        );
        assert_eq!(
            req.headers.get("x-org-id").map(String::as_str),
            Some(TEST_ORG)
        );
        seen_srv
            .lock()
            .unwrap()
            .push(format!("{} {}", req.method, req.target));

        match (req.method.as_str(), req.target.as_str()) {
            ("GET", "/v1/flow/status") => MockResp {
                status: 200,
                reason: "OK",
                headers: vec![],
                body: r#"{"reachable":true,"version":"1.8.16"}"#.into(),
            },
            ("GET", "/v1/flow/workflows?page=2&size=25") => MockResp {
                status: 200,
                reason: "OK",
                headers: vec![],
                body: format!(
                    r#"{{"flows":[{{"id":"{TEST_WF_ID}","name":"triage"}}],"total":1,"page":2,"size":25,"pages":1}}"#
                ),
            },
            ("POST", "/v1/flow/workflows") => {
                let parsed: serde_json::Value = serde_json::from_str(&req.body).unwrap();
                assert_eq!(parsed["name"], "triage");
                assert_eq!(parsed["data"]["schema"], GRAPH_SCHEMA_VERSION);
                assert_eq!(parsed["data"]["edges"][0]["sourceHandle"], "out");
                MockResp {
                    status: 200,
                    reason: "OK",
                    headers: vec![],
                    body: format!(
                        r#"{{"id":"{TEST_WF_ID}","name":"triage","description":"route tickets","data":{{"schema":"hanzo.flow/v1","nodes":[{{"id":"n1","type":"input"}}],"edges":[]}}}}"#
                    ),
                }
            }
            ("GET", p) if p == format!("/v1/flow/workflows/{TEST_WF_ID}") => MockResp {
                status: 200,
                reason: "OK",
                headers: vec![],
                body: format!(r#"{{"id":"{TEST_WF_ID}","name":"triage","locked":false}}"#),
            },
            ("PATCH", p) if p == format!("/v1/flow/workflows/{TEST_WF_ID}") => {
                let parsed: serde_json::Value = serde_json::from_str(&req.body).unwrap();
                assert_eq!(parsed, json!({"name": "triage-v2", "locked": true}));
                MockResp {
                    status: 200,
                    reason: "OK",
                    headers: vec![],
                    body: format!(r#"{{"id":"{TEST_WF_ID}","name":"triage-v2","locked":true}}"#),
                }
            }
            ("POST", "/v1/flow/runs") => {
                let parsed: serde_json::Value = serde_json::from_str(&req.body).unwrap();
                assert_eq!(parsed["workflow"], TEST_WF_ID);
                assert_eq!(parsed["input"], "summarize");
                assert_eq!(parsed["session"], "sess-1");
                MockResp {
                    status: 200,
                    reason: "OK",
                    headers: vec![],
                    body: r#"{"session_id":"sess-1","outputs":[{"text":"done"}]}"#.into(),
                }
            }
            ("GET", p) if p == format!("/v1/flow/runs?workflow={TEST_WF_ID}") => MockResp {
                status: 200,
                reason: "OK",
                headers: vec![],
                body: r#"{"vertex_builds":{"n1":[{"status":"ok"}]}}"#.into(),
            },
            ("DELETE", p) if p == format!("/v1/flow/workflows/{TEST_WF_ID}") => MockResp {
                status: 204,
                reason: "No Content",
                headers: vec![],
                body: String::new(),
            },
            other => panic!("unexpected request: {other:?}"),
        }
    });

    let client = FlowClient::new(
        ClientConfig::new()
            .base_url(base_url)
            .token(TEST_TOKEN)
            .org_id(TEST_ORG),
    );

    let st = client.status().expect("status");
    assert!(st.reachable);
    assert_eq!(st.version.as_deref(), Some("1.8.16"));

    let list = client
        .list_workflows(&ListOptions {
            page: Some(2),
            size: Some(25),
        })
        .expect("list_workflows");
    assert_eq!(list.total, 1);
    assert_eq!(list.workflows[0].id, TEST_WF_ID);

    let mut graph = WorkflowGraph::new();
    graph.nodes.push(GraphNode {
        id: "n1".into(),
        node_type: "input".into(),
        data: None,
        position: None,
    });
    graph.edges.push(GraphEdge {
        id: "e1".into(),
        source: "n1".into(),
        source_handle: Some("out".into()),
        target: "n2".into(),
        target_handle: Some("in".into()),
    });

    let created = client
        .create_workflow(&CreateWorkflowRequest {
            name: "triage".into(),
            description: Some("route tickets".into()),
            data: Some(graph),
        })
        .expect("create_workflow");
    assert_eq!(created.id, TEST_WF_ID);
    assert_eq!(
        created.data.as_ref().map(|g| g.schema.as_str()),
        Some(GRAPH_SCHEMA_VERSION)
    );

    let fetched = client.get_workflow(TEST_WF_ID).expect("get_workflow");
    assert!(!fetched.locked);

    let updated = client
        .update_workflow(
            TEST_WF_ID,
            &UpdateWorkflowRequest {
                name: Some("triage-v2".into()),
                locked: Some(true),
                ..Default::default()
            },
        )
        .expect("update_workflow");
    assert_eq!(updated.name, "triage-v2");
    assert!(updated.locked);

    let mut run_req = RunRequest::new(TEST_WF_ID, "summarize");
    run_req.session = Some("sess-1".into());
    run_req.tweaks = Some(json!({"n2": {"temperature": 0}}));
    let ran = client.run(&run_req).expect("run");
    assert_eq!(ran.session_id.as_deref(), Some("sess-1"));
    assert_eq!(ran.outputs.len(), 1);

    let runs = client.list_runs(TEST_WF_ID).expect("list_runs");
    assert!(runs.vertex_builds.contains_key("n1"));

    client.delete_workflow(TEST_WF_ID).expect("delete_workflow");

    handle.join().expect("server thread");
    assert_eq!(seen.lock().unwrap().len(), 8);
}

#[test]
fn decodes_rfc7807_api_error_with_request_id() {
    let (base_url, handle) = spawn_mock_server(1, |_req| MockResp {
        status: 404,
        reason: "Not Found",
        headers: vec![("X-Request-Id", "req-rust-404")],
        body: r#"{"title":"Not Found","status":404,"detail":"workflow not found"}"#.into(),
    });

    let client = FlowClient::new(ClientConfig::new().base_url(base_url));
    let err = client.get_workflow(TEST_WF_ID).expect_err("expected 404");
    match err {
        FlowError::Api(api) => {
            assert_eq!(api.status, 404);
            assert_eq!(api.title, "Not Found");
            assert_eq!(api.detail, "workflow not found");
            assert_eq!(api.request_id.as_deref(), Some("req-rust-404"));
            assert!(api.to_string().contains("req-rust-404"));
        }
        other => panic!("expected FlowError::Api, got {other:?}"),
    }
    handle.join().expect("server thread");
}

#[test]
fn validates_empty_inputs_before_network() {
    let client = FlowClient::new(ClientConfig::new());
    assert!(matches!(
        client.get_workflow("  "),
        Err(FlowError::InvalidInput(_))
    ));
    assert!(matches!(
        client.create_workflow(&CreateWorkflowRequest {
            name: String::new(),
            description: None,
            data: None,
        }),
        Err(FlowError::InvalidInput(_))
    ));
    assert!(matches!(
        client.run(&RunRequest::new("", "hi")),
        Err(FlowError::InvalidInput(_))
    ));
    assert!(matches!(
        client.list_runs(""),
        Err(FlowError::InvalidInput(_))
    ));
}
