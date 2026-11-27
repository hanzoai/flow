package flow

import (
	"encoding/json"
	"fmt"
	"net/http"
)

// GraphSchemaVersion is the canonical portable workflow graph schema identifier.
const GraphSchemaVersion = "hanzo.flow/v1"

// Status is returned by GET /v1/flow/status.
type Status struct {
	Reachable bool   `json:"reachable"`
	Version   string `json:"version,omitempty"`
}

// Position places a node on the visual canvas.
type Position struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
}

// GraphNode is a step inside a hanzo.flow/v1 WorkflowGraph.
type GraphNode struct {
	ID       string          `json:"id"`
	Type     string          `json:"type,omitempty"`
	Data     json.RawMessage `json:"data,omitempty"`
	Position *Position       `json:"position,omitempty"`
}

// GraphEdge wires an upstream output handle to a downstream input handle.
type GraphEdge struct {
	ID           string `json:"id,omitempty"`
	Source       string `json:"source"`
	SourceHandle string `json:"sourceHandle,omitempty"`
	Target       string `json:"target"`
	TargetHandle string `json:"targetHandle,omitempty"`
}

// WorkflowGraph is the portable hanzo.flow/v1 workflow DAG document.
type WorkflowGraph struct {
	Schema string      `json:"schema,omitempty"`
	Nodes  []GraphNode `json:"nodes"`
	Edges  []GraphEdge `json:"edges"`
}

// NewWorkflowGraph returns an empty hanzo.flow/v1 graph with non-nil slices.
func NewWorkflowGraph() WorkflowGraph {
	return WorkflowGraph{
		Schema: GraphSchemaVersion,
		Nodes:  []GraphNode{},
		Edges:  []GraphEdge{},
	}
}

// MarshalJSON ensures Schema defaults to GraphSchemaVersion and Nodes/Edges
// serialize as JSON arrays rather than null.
func (g WorkflowGraph) MarshalJSON() ([]byte, error) {
	type alias struct {
		Schema string      `json:"schema"`
		Nodes  []GraphNode `json:"nodes"`
		Edges  []GraphEdge `json:"edges"`
	}
	out := alias{
		Schema: g.Schema,
		Nodes:  g.Nodes,
		Edges:  g.Edges,
	}
	if out.Schema == "" {
		out.Schema = GraphSchemaVersion
	}
	if out.Nodes == nil {
		out.Nodes = []GraphNode{}
	}
	if out.Edges == nil {
		out.Edges = []GraphEdge{}
	}
	return json.Marshal(out)
}

// Workflow is a workflow record returned by /v1/flow/workflows.
type Workflow struct {
	ID           string          `json:"id"`
	Name         string          `json:"name"`
	Description  string          `json:"description,omitempty"`
	Data         *WorkflowGraph  `json:"data,omitempty"`
	Locked       bool            `json:"locked,omitempty"`
	FolderID     string          `json:"folder_id,omitempty"`
	EndpointName string          `json:"endpoint_name,omitempty"`
	Tags         []string        `json:"tags,omitempty"`
	UpdatedAt    string          `json:"updated_at,omitempty"`
	Raw          json.RawMessage `json:"-"`
}

// UnmarshalJSON populates typed fields and preserves the verbatim JSON payload.
func (w *Workflow) UnmarshalJSON(b []byte) error {
	type alias Workflow
	var decoded alias
	if err := json.Unmarshal(b, &decoded); err != nil {
		return err
	}
	*w = Workflow(decoded)
	w.Raw = append(json.RawMessage(nil), b...)
	return nil
}

// ListOptions controls pagination on GET /v1/flow/workflows.
type ListOptions struct {
	Page int
	Size int
}

// WorkflowList is the response of GET /v1/flow/workflows. It decodes both
// paginated objects ({"flows": [...], "total": ...} or {"items": [...]}) and
// bare JSON arrays ([...]).
type WorkflowList struct {
	Workflows []Workflow      `json:"flows"`
	Total     int             `json:"total,omitempty"`
	Page      int             `json:"page,omitempty"`
	Size      int             `json:"size,omitempty"`
	Pages     int             `json:"pages,omitempty"`
	Raw       json.RawMessage `json:"-"`
}

// UnmarshalJSON supports both paginated envelopes and plain workflow arrays.
func (l *WorkflowList) UnmarshalJSON(b []byte) error {
	l.Raw = append(json.RawMessage(nil), b...)
	var arr []Workflow
	if err := json.Unmarshal(b, &arr); err == nil {
		l.Workflows = arr
		l.Total = len(arr)
		return nil
	}
	var env struct {
		Flows []Workflow `json:"flows"`
		Items []Workflow `json:"items"`
		Total int        `json:"total"`
		Page  int        `json:"page"`
		Size  int        `json:"size"`
		Pages int        `json:"pages"`
	}
	if err := json.Unmarshal(b, &env); err != nil {
		return err
	}
	if env.Flows != nil {
		l.Workflows = env.Flows
	} else {
		l.Workflows = env.Items
	}
	l.Total = env.Total
	if l.Total == 0 && len(l.Workflows) > 0 {
		l.Total = len(l.Workflows)
	}
	l.Page = env.Page
	l.Size = env.Size
	l.Pages = env.Pages
	return nil
}

// CreateWorkflowRequest is the body for POST /v1/flow/workflows.
type CreateWorkflowRequest struct {
	Name        string         `json:"name"`
	Description string         `json:"description,omitempty"`
	Data        *WorkflowGraph `json:"data,omitempty"`
}

// UpdateWorkflowRequest is the partial patch body for PATCH /v1/flow/workflows/{id}.
type UpdateWorkflowRequest struct {
	Name        *string        `json:"name,omitempty"`
	Description *string        `json:"description,omitempty"`
	Data        *WorkflowGraph `json:"data,omitempty"`
	Locked      *bool          `json:"locked,omitempty"`
}

// RunRequest is the body for POST /v1/flow/runs.
type RunRequest struct {
	Workflow string          `json:"workflow"`
	Input    string          `json:"input,omitempty"`
	Session  string          `json:"session,omitempty"`
	Tweaks   json.RawMessage `json:"tweaks,omitempty"`
}

// RunResponse is the synchronous result of POST /v1/flow/runs.
type RunResponse struct {
	SessionID string            `json:"session_id,omitempty"`
	Outputs   []json.RawMessage `json:"outputs,omitempty"`
	Raw       json.RawMessage   `json:"-"`
}

// UnmarshalJSON decodes RunResponse and retains the raw JSON payload.
func (r *RunResponse) UnmarshalJSON(b []byte) error {
	type alias RunResponse
	var decoded alias
	if err := json.Unmarshal(b, &decoded); err != nil {
		return err
	}
	*r = RunResponse(decoded)
	r.Raw = append(json.RawMessage(nil), b...)
	return nil
}

// RunsResponse is the response of GET /v1/flow/runs?workflow={id}.
type RunsResponse struct {
	VertexBuilds map[string]json.RawMessage `json:"vertex_builds,omitempty"`
	Runs         []json.RawMessage          `json:"runs,omitempty"`
	Raw          json.RawMessage            `json:"-"`
}

// UnmarshalJSON accepts both keyed build maps and arrays of run records.
func (r *RunsResponse) UnmarshalJSON(b []byte) error {
	r.Raw = append(json.RawMessage(nil), b...)
	var arr []json.RawMessage
	if err := json.Unmarshal(b, &arr); err == nil {
		r.Runs = arr
		return nil
	}
	var env struct {
		VertexBuilds map[string]json.RawMessage `json:"vertex_builds"`
		Runs         []json.RawMessage          `json:"runs"`
	}
	if err := json.Unmarshal(b, &env); err != nil {
		return err
	}
	r.VertexBuilds = env.VertexBuilds
	r.Runs = env.Runs
	return nil
}

// APIError is a typed HTTP error returned by the Hanzo Flow API.
type APIError struct {
	Status    int    `json:"status"`
	Title     string `json:"title,omitempty"`
	Detail    string `json:"detail,omitempty"`
	RequestID string `json:"request_id,omitempty"`
}

// Error implements error.
func (e *APIError) Error() string {
	title := e.Title
	if title == "" {
		title = http.StatusText(e.Status)
	}
	switch {
	case e.Detail != "" && e.RequestID != "":
		return fmt.Sprintf("flow api %d %s: %s (request_id=%s)", e.Status, title, e.Detail, e.RequestID)
	case e.Detail != "":
		return fmt.Sprintf("flow api %d %s: %s", e.Status, title, e.Detail)
	case e.RequestID != "":
		return fmt.Sprintf("flow api %d %s (request_id=%s)", e.Status, title, e.RequestID)
	default:
		return fmt.Sprintf("flow api %d %s", e.Status, title)
	}
}
