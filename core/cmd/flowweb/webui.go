package main

import (
	"embed"
	"io"
	"io/fs"
	"net/http"
	"net/http/httputil"
	"net/url"
	"path"
	"strings"
)

// frontend is the built flow UI. At a plain `go build` this is the committed
// landing placeholder (frontend/index.html); the image build runs the Vite build
// (`src/frontend` → `build/`) and OVERWRITES this directory with the real bundle
// BEFORE `go build`, so the shipped binary carries the full app. Same one-artifact
// discipline as hanzoai/world's webui/dist.
//
//go:embed all:frontend
var frontendFS embed.FS

// apiPrefixes go to the backend, never the SPA — an unmatched path here is the
// backend's real JSON 404, never index.html (so a client never gets HTML where it
// expects JSON). Everything else is a client-side route → the SPA shell.
var apiPrefixes = []string{
	"/api/", "/health", "/health_check", "/openapi.json", "/docs", "/redoc",
	"/.well-known/", "/logs", "/metrics",
}

type handler struct {
	fsys  fs.FS
	index []byte
	proxy *httputil.ReverseProxy
}

func newHandler(backend string) (*handler, error) {
	sub, err := fs.Sub(frontendFS, "frontend")
	if err != nil {
		return nil, err
	}
	index, err := fs.ReadFile(sub, "index.html")
	if err != nil {
		return nil, err
	}
	u, err := url.Parse(backend)
	if err != nil {
		return nil, err
	}
	return &handler{fsys: sub, index: index, proxy: httputil.NewSingleHostReverseProxy(u)}, nil
}

func (h *handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	upath := r.URL.Path
	if !strings.HasPrefix(upath, "/") {
		upath = "/" + upath
	}
	// API + backend surfaces → the flow backend verbatim (all methods).
	for _, p := range apiPrefixes {
		if upath == strings.TrimSuffix(p, "/") || strings.HasPrefix(upath, p) {
			h.proxy.ServeHTTP(w, r)
			return
		}
	}
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	// Exact static asset if it exists, else the SPA shell — the app's own home /
	// login IS the landing, so one binary serves landing + app.
	name := path.Clean(strings.TrimPrefix(upath, "/"))
	if name != "" && name != "." && h.serveAsset(w, r, name) {
		return
	}
	h.serveIndex(w, r)
}

// serveAsset writes the embedded file at name, or returns false (writing nothing)
// when it is missing or a directory, so the caller falls back to the SPA shell.
func (h *handler) serveAsset(w http.ResponseWriter, r *http.Request, name string) bool {
	f, err := h.fsys.Open(name)
	if err != nil {
		return false
	}
	defer f.Close()
	info, err := f.Stat()
	if err != nil || info.IsDir() {
		return false
	}
	rs, ok := f.(io.ReadSeeker)
	if !ok {
		return false
	}
	// Vite emits content-hashed filenames under assets/ — cache them hard.
	if strings.HasPrefix(name, "assets/") {
		w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
	}
	http.ServeContent(w, r, name, info.ModTime(), rs)
	return true
}

// serveIndex writes the SPA shell (never cached, so a new build is picked up at
// once; the fingerprinted assets it references are cached hard above).
func (h *handler) serveIndex(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("Cache-Control", "no-cache")
	w.WriteHeader(http.StatusOK)
	if r.Method != http.MethodHead {
		_, _ = w.Write(h.index)
	}
}

// compile-time assertion: handler is a stdlib http.Handler.
var _ http.Handler = (*handler)(nil)
