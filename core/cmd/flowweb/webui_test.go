package main

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestHandlerRoutes(t *testing.T) {
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = io.WriteString(w, `{"path":"`+r.URL.Path+`"}`)
	}))
	defer backend.Close()

	h, err := newHandler(backend.URL)
	if err != nil {
		t.Fatal(err)
	}

	cases := []struct {
		method, path string
		backend      bool
		status       int
	}{
		{http.MethodGet, "/v1/version", true, http.StatusOK},
		{http.MethodPost, "/v1/login", true, http.StatusOK},
		{http.MethodGet, "/v1", true, http.StatusOK},
		{http.MethodGet, "/v2/files", true, http.StatusOK},
		{http.MethodGet, "/health_check", true, http.StatusOK},
		{http.MethodGet, "/logs-stream", true, http.StatusOK},
		{http.MethodGet, "/", false, http.StatusOK},
		{http.MethodGet, "/flows", false, http.StatusOK},
		{http.MethodGet, "/v10", false, http.StatusOK},
		{http.MethodPost, "/flows", false, http.StatusMethodNotAllowed},
	}
	for _, c := range cases {
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, httptest.NewRequest(c.method, c.path, nil))
		if rec.Code != c.status {
			t.Errorf("%s %s: status %d, want %d", c.method, c.path, rec.Code, c.status)
			continue
		}
		body := rec.Body.String()
		proxied := strings.Contains(body, `{"path":"`+c.path+`"}`)
		if proxied != c.backend {
			t.Errorf("%s %s: proxied=%v, want %v (body %.60q)", c.method, c.path, proxied, c.backend, body)
		}
		if !c.backend && c.status == http.StatusOK && !strings.Contains(body, "<html") {
			t.Errorf("%s %s: want the SPA shell, got %.60q", c.method, c.path, body)
		}
	}
}
