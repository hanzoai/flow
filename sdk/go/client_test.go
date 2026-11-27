package flow

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

const (
	testWFID  = "8f14e45f-ceea-467a-8a3b-111111111111"
	testToken = "hz-test-token"
	testOrg   = "hanzo"
)

func TestNewClientDefaults(t *testing.T) {
	c := NewClient()
	if c.baseURL != DefaultBaseURL {
		t.Fatalf("baseURL = %q, want %q", c.baseURL, DefaultBaseURL)
	}
	if c.httpClient == nil {
		t.Fatal("expected default httpClient")
	}
}

func TestClientAllCanonicalEndpoints(t *testing.T) {
	var seen []string

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if got := r.Header.Get("Authorization"); got != "Bearer "+testToken {
			t.Errorf("%s %s: Authorization = %q, want Bearer %s", r.Method, r.URL.Path, got, testToken)
		}
		if got := r.Header.Get("X-Org-Id"); got != testOrg {
			t.Errorf("%s %s: X-Org-Id = %q, want %s", r.Method, r.URL.Path, got, testOrg)
		}
		seen = append(seen, r.Method+" "+r.URL.RequestURI())
		w.Header().Set("Content-Type", "application/json")

		switch {
		case r.Method == http.MethodGet && r.URL.Path == "/v1/flow/status":
			_, _ = w.Write([]byte(`{"reachable":true,"version":"1.8.16"}`))

		case r.Method == http.MethodGet && r.URL.Path == "/v1/flow/workflows":
			if r.URL.Query().Get("page") != "2" || r.URL.Query().Get("size") != "25" {
				t.Errorf("unexpected query: %s", r.URL.RawQuery)
			}
			_, _ = w.Write([]byte(`{"flows":[{"id":"` + testWFID + `","name":"triage"}],"total":1,"page":2,"size":25,"pages":1}`))

		case r.Method == http.MethodPost && r.URL.Path == "/v1/flow/workflows":
			var req CreateWorkflowRequest
			if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
				t.Fatalf("decode create: %v", err)
			}
			if req.Name != "triage" || req.Description != "route tickets" {
				t.Errorf("unexpected create req: %+v", req)
			}
			if req.Data == nil || req.Data.Schema != GraphSchemaVersion || len(req.Data.Nodes) != 2 || len(req.Data.Edges) != 1 {
				t.Errorf("unexpected create graph: %+v", req.Data)
			}
			_, _ = w.Write([]byte(`{"id":"` + testWFID + `","name":"triage","description":"route tickets","data":{"schema":"hanzo.flow/v1","nodes":[{"id":"n1","type":"input"},{"id":"n2","type":"llm"}],"edges":[{"id":"e1","source":"n1","sourceHandle":"out","target":"n2","targetHandle":"in"}]}}`))

		case r.Method == http.MethodGet && r.URL.Path == "/v1/flow/workflows/"+testWFID:
			_, _ = w.Write([]byte(`{"id":"` + testWFID + `","name":"triage","locked":false,"data":{"schema":"hanzo.flow/v1","nodes":[],"edges":[]}}`))

		case r.Method == http.MethodPatch && r.URL.Path == "/v1/flow/workflows/"+testWFID:
			var raw map[string]any
			if err := json.NewDecoder(r.Body).Decode(&raw); err != nil {
				t.Fatalf("decode patch: %v", err)
			}
			if raw["name"] != "triage-v2" || raw["locked"] != true {
				t.Errorf("unexpected patch body: %v", raw)
			}
			if _, ok := raw["description"]; ok {
				t.Errorf("omitted description leaked into patch: %v", raw)
			}
			_, _ = w.Write([]byte(`{"id":"` + testWFID + `","name":"triage-v2","locked":true}`))

		case r.Method == http.MethodDelete && r.URL.Path == "/v1/flow/workflows/"+testWFID:
			w.WriteHeader(http.StatusNoContent)

		case r.Method == http.MethodPost && r.URL.Path == "/v1/flow/runs":
			var req RunRequest
			if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
				t.Fatalf("decode run: %v", err)
			}
			if req.Workflow != testWFID || req.Input != "summarize" || req.Session != "sess-1" {
				t.Errorf("unexpected run req: %+v", req)
			}
			_, _ = w.Write([]byte(`{"session_id":"sess-1","outputs":[{"text":"done"}]}`))

		case r.Method == http.MethodGet && r.URL.Path == "/v1/flow/runs":
			if r.URL.Query().Get("workflow") != testWFID {
				t.Errorf("workflow query = %q", r.URL.Query().Get("workflow"))
			}
			_, _ = w.Write([]byte(`{"vertex_builds":{"n1":[{"status":"ok"}]}}`))

		default:
			http.NotFound(w, r)
		}
	}))
	defer srv.Close()

	c := NewClient(
		WithBaseURL(srv.URL+"/"),
		WithToken(testToken),
		WithOrgID(testOrg),
		WithHTTPClient(srv.Client()),
	)
	ctx := context.Background()

	st, err := c.Status(ctx)
	if err != nil {
		t.Fatalf("Status: %v", err)
	}
	if !st.Reachable || st.Version != "1.8.16" {
		t.Fatalf("unexpected status: %+v", st)
	}

	list, err := c.ListWorkflows(ctx, ListOptions{Page: 2, Size: 25})
	if err != nil {
		t.Fatalf("ListWorkflows: %v", err)
	}
	if len(list.Workflows) != 1 || list.Total != 1 || list.Workflows[0].ID != testWFID {
		t.Fatalf("unexpected list: %+v", list)
	}

	graph := WorkflowGraph{
		Nodes: []GraphNode{
			{ID: "n1", Type: "input"},
			{ID: "n2", Type: "llm"},
		},
		Edges: []GraphEdge{
			{ID: "e1", Source: "n1", SourceHandle: "out", Target: "n2", TargetHandle: "in"},
		},
	}
	created, err := c.CreateWorkflow(ctx, CreateWorkflowRequest{
		Name:        "triage",
		Description: "route tickets",
		Data:        &graph,
	})
	if err != nil {
		t.Fatalf("CreateWorkflow: %v", err)
	}
	if created.ID != testWFID || created.Data == nil || created.Data.Schema != GraphSchemaVersion {
		t.Fatalf("unexpected created workflow: %+v", created)
	}

	got, err := c.GetWorkflow(ctx, testWFID)
	if err != nil {
		t.Fatalf("GetWorkflow: %v", err)
	}
	if got.ID != testWFID || got.Locked {
		t.Fatalf("unexpected workflow: %+v", got)
	}

	newName := "triage-v2"
	locked := true
	updated, err := c.UpdateWorkflow(ctx, testWFID, UpdateWorkflowRequest{
		Name:   &newName,
		Locked: &locked,
	})
	if err != nil {
		t.Fatalf("UpdateWorkflow: %v", err)
	}
	if updated.Name != "triage-v2" || !updated.Locked {
		t.Fatalf("unexpected updated workflow: %+v", updated)
	}

	runRes, err := c.Run(ctx, RunRequest{
		Workflow: testWFID,
		Input:    "summarize",
		Session:  "sess-1",
		Tweaks:   json.RawMessage(`{"n2":{"temperature":0}}`),
	})
	if err != nil {
		t.Fatalf("Run: %v", err)
	}
	if runRes.SessionID != "sess-1" || len(runRes.Outputs) != 1 {
		t.Fatalf("unexpected run response: %+v", runRes)
	}

	runs, err := c.ListRuns(ctx, testWFID)
	if err != nil {
		t.Fatalf("ListRuns: %v", err)
	}
	if _, ok := runs.VertexBuilds["n1"]; !ok {
		t.Fatalf("expected vertex_builds[n1], got %+v", runs)
	}

	if err := c.DeleteWorkflow(ctx, testWFID); err != nil {
		t.Fatalf("DeleteWorkflow: %v", err)
	}
	if len(seen) != 8 {
		t.Fatalf("expected 8 requests, got %d: %v", len(seen), seen)
	}
}

func TestListWorkflowsArrayEnvelope(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`[{"id":"a","name":"one"},{"id":"b","name":"two"}]`))
	}))
	defer srv.Close()

	c := NewClient(WithBaseURL(srv.URL))
	list, err := c.ListWorkflows(context.Background(), ListOptions{})
	if err != nil {
		t.Fatalf("ListWorkflows: %v", err)
	}
	if len(list.Workflows) != 2 || list.Total != 2 {
		t.Fatalf("unexpected array list: %+v", list)
	}
}

func TestAPIErrorDecoding(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/problem+json")
		w.Header().Set("X-Request-Id", "req-xyz-123")
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"title":"Not Found","status":404,"detail":"workflow not found"}`))
	}))
	defer srv.Close()

	c := NewClient(WithBaseURL(srv.URL))
	_, err := c.GetWorkflow(context.Background(), testWFID)
	if err == nil {
		t.Fatal("expected APIError")
	}
	var apiErr *APIError
	if !errors.As(err, &apiErr) {
		t.Fatalf("expected *APIError, got %T: %v", err, err)
	}
	if apiErr.Status != http.StatusNotFound || apiErr.Title != "Not Found" ||
		apiErr.Detail != "workflow not found" || apiErr.RequestID != "req-xyz-123" {
		t.Fatalf("unexpected APIError: %+v", apiErr)
	}
	if !strings.Contains(apiErr.Error(), "req-xyz-123") {
		t.Fatalf("Error() missing request id: %q", apiErr.Error())
	}
}

func TestContextCancellation(t *testing.T) {
	blocked := make(chan struct{})
	srv := httptest.NewServer(http.HandlerFunc(func(_ http.ResponseWriter, _ *http.Request) {
		<-blocked
	}))
	defer func() {
		close(blocked)
		srv.Close()
	}()

	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Millisecond)
	defer cancel()

	c := NewClient(WithBaseURL(srv.URL))
	_, err := c.Status(ctx)
	if !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("expected context.DeadlineExceeded, got %v", err)
	}
}

func TestInputValidation(t *testing.T) {
	c := NewClient()
	ctx := context.Background()
	if _, err := c.GetWorkflow(ctx, " "); err == nil {
		t.Fatal("expected error for empty GetWorkflow id")
	}
	if _, err := c.CreateWorkflow(ctx, CreateWorkflowRequest{}); err == nil {
		t.Fatal("expected error for empty CreateWorkflow name")
	}
	if _, err := c.Run(ctx, RunRequest{}); err == nil {
		t.Fatal("expected error for empty Run workflow")
	}
	if _, err := c.ListRuns(ctx, ""); err == nil {
		t.Fatal("expected error for empty ListRuns workflowID")
	}
}
