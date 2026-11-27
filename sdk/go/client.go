// Package flow provides a zero-dependency Go client for the canonical Hanzo Flow
// REST API (/v1/flow/*).
package flow

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

// DefaultBaseURL is the canonical Hanzo API origin.
const DefaultBaseURL = "https://api.hanzo.ai"

const (
	defaultTimeout = 60 * time.Second
	maxBodyBytes   = 32 << 20
)

// Option configures a Client.
type Option func(*Client)

// WithBaseURL overrides the API origin (defaults to DefaultBaseURL).
func WithBaseURL(baseURL string) Option {
	return func(c *Client) {
		if trimmed := strings.TrimRight(strings.TrimSpace(baseURL), "/"); trimmed != "" {
			c.baseURL = trimmed
		}
	}
}

// WithToken sets the Hanzo IAM Bearer token sent in Authorization headers.
func WithToken(token string) Option {
	return func(c *Client) {
		c.token = strings.TrimSpace(token)
	}
}

// WithOrgID sets the active organization slug sent in the X-Org-Id header.
func WithOrgID(orgID string) Option {
	return func(c *Client) {
		c.orgID = strings.TrimSpace(orgID)
	}
}

// WithHTTPClient provides a custom *http.Client (timeouts, transport, TLS).
func WithHTTPClient(hc *http.Client) Option {
	return func(c *Client) {
		if hc != nil {
			c.httpClient = hc
		}
	}
}

// Client talks to the canonical Hanzo Flow REST API (/v1/flow/*).
type Client struct {
	baseURL    string
	token      string
	orgID      string
	httpClient *http.Client
}

// NewClient creates a new Flow API client with the given functional options.
func NewClient(opts ...Option) *Client {
	c := &Client{
		baseURL:    DefaultBaseURL,
		httpClient: &http.Client{Timeout: defaultTimeout},
	}
	for _, opt := range opts {
		if opt != nil {
			opt(c)
		}
	}
	return c
}

// Status reports reachability and version via GET /v1/flow/status.
func (c *Client) Status(ctx context.Context) (*Status, error) {
	var out Status
	if err := c.do(ctx, http.MethodGet, "/v1/flow/status", nil, nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// ListWorkflows returns the caller's org-scoped workflows via GET /v1/flow/workflows.
func (c *Client) ListWorkflows(ctx context.Context, opts ListOptions) (*WorkflowList, error) {
	q := url.Values{}
	if opts.Page > 0 {
		q.Set("page", strconv.Itoa(opts.Page))
	}
	if opts.Size > 0 {
		q.Set("size", strconv.Itoa(opts.Size))
	}
	var out WorkflowList
	if err := c.do(ctx, http.MethodGet, "/v1/flow/workflows", q, nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// GetWorkflow fetches a single workflow record via GET /v1/flow/workflows/{id}.
func (c *Client) GetWorkflow(ctx context.Context, id string) (*Workflow, error) {
	seg, err := workflowSegment(id)
	if err != nil {
		return nil, err
	}
	var out Workflow
	if err := c.do(ctx, http.MethodGet, "/v1/flow/workflows/"+seg, nil, nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// CreateWorkflow creates a workflow in the caller's org via POST /v1/flow/workflows.
func (c *Client) CreateWorkflow(ctx context.Context, req CreateWorkflowRequest) (*Workflow, error) {
	if strings.TrimSpace(req.Name) == "" {
		return nil, errors.New("flow: workflow name is required")
	}
	var out Workflow
	if err := c.do(ctx, http.MethodPost, "/v1/flow/workflows", nil, req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// UpdateWorkflow patches fields on an existing workflow via PATCH /v1/flow/workflows/{id}.
func (c *Client) UpdateWorkflow(ctx context.Context, id string, req UpdateWorkflowRequest) (*Workflow, error) {
	seg, err := workflowSegment(id)
	if err != nil {
		return nil, err
	}
	var out Workflow
	if err := c.do(ctx, http.MethodPatch, "/v1/flow/workflows/"+seg, nil, req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// DeleteWorkflow deletes a workflow and its recorded runs via DELETE /v1/flow/workflows/{id}.
func (c *Client) DeleteWorkflow(ctx context.Context, id string) error {
	seg, err := workflowSegment(id)
	if err != nil {
		return err
	}
	return c.do(ctx, http.MethodDelete, "/v1/flow/workflows/"+seg, nil, nil, nil)
}

// Run executes a workflow synchronously via POST /v1/flow/runs.
func (c *Client) Run(ctx context.Context, req RunRequest) (*RunResponse, error) {
	if strings.TrimSpace(req.Workflow) == "" {
		return nil, errors.New("flow: workflow ID is required")
	}
	var out RunResponse
	if err := c.do(ctx, http.MethodPost, "/v1/flow/runs", nil, req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// ListRuns reads recorded runs for a workflow via GET /v1/flow/runs?workflow={id}.
func (c *Client) ListRuns(ctx context.Context, workflowID string) (*RunsResponse, error) {
	wf := strings.TrimSpace(workflowID)
	if wf == "" {
		return nil, errors.New("flow: workflow ID is required")
	}
	q := url.Values{"workflow": {wf}}
	var out RunsResponse
	if err := c.do(ctx, http.MethodGet, "/v1/flow/runs", q, nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

func workflowSegment(id string) (string, error) {
	trimmed := strings.TrimSpace(id)
	if trimmed == "" {
		return "", errors.New("flow: workflow ID is required")
	}
	return url.PathEscape(trimmed), nil
}

func (c *Client) do(ctx context.Context, method, path string, query url.Values, body any, out any) error {
	endpoint := c.baseURL + path
	if len(query) > 0 {
		endpoint += "?" + query.Encode()
	}

	var rdr io.Reader
	if body != nil {
		payload, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("flow: marshal request: %w", err)
		}
		rdr = bytes.NewReader(payload)
	}

	req, err := http.NewRequestWithContext(ctx, method, endpoint, rdr)
	if err != nil {
		return fmt.Errorf("flow: build request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if c.token != "" {
		req.Header.Set("Authorization", "Bearer "+c.token)
	}
	if c.orgID != "" {
		req.Header.Set("X-Org-Id", c.orgID)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer func() { _ = resp.Body.Close() }()

	data, err := io.ReadAll(io.LimitReader(resp.Body, maxBodyBytes))
	if err != nil {
		return fmt.Errorf("flow: read response: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return decodeAPIError(resp.StatusCode, resp.Header, data)
	}

	if out == nil || len(bytes.TrimSpace(data)) == 0 {
		return nil
	}
	if err := json.Unmarshal(data, out); err != nil {
		return fmt.Errorf("flow: decode response: %w", err)
	}
	return nil
}

func decodeAPIError(status int, header http.Header, body []byte) *APIError {
	apiErr := &APIError{
		Status:    status,
		Title:     http.StatusText(status),
		RequestID: header.Get("X-Request-Id"),
	}
	if len(bytes.TrimSpace(body)) == 0 {
		return apiErr
	}
	var env struct {
		Status    int             `json:"status"`
		Title     string          `json:"title"`
		Detail    json.RawMessage `json:"detail"`
		Message   string          `json:"message"`
		Error     string          `json:"error"`
		RequestID string          `json:"request_id"`
	}
	if err := json.Unmarshal(body, &env); err == nil {
		if env.Status != 0 {
			apiErr.Status = env.Status
		}
		if env.Title != "" {
			apiErr.Title = env.Title
		}
		if env.RequestID != "" && apiErr.RequestID == "" {
			apiErr.RequestID = env.RequestID
		}
		if len(env.Detail) > 0 {
			var s string
			if json.Unmarshal(env.Detail, &s) == nil {
				apiErr.Detail = s
			} else {
				apiErr.Detail = string(env.Detail)
			}
		} else if env.Message != "" {
			apiErr.Detail = env.Message
		} else if env.Error != "" {
			apiErr.Detail = env.Error
		}
	}
	if apiErr.Detail == "" {
		apiErr.Detail = strings.TrimSpace(string(body))
	}
	return apiErr
}
