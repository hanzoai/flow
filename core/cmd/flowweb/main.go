// Command flowweb is the ONE native binary that fronts flow.hanzo.ai.
//
// It go:embeds the built flow UI (the Vite frontend + the landing) and serves it
// directly, while reverse-proxying the API surface to the flow backend. One image,
// one origin — no separate static landing site, no second app host, no
// disabled-ingress split. This mirrors hanzoai/world and hanzoai/cloud's
// embedded-SPA pattern: the Go binary is the front door; the Python backend (or,
// over time, the Go flow-core engine next door in this module) answers the API.
package main

import (
	"log"
	"net/http"
	"os"
	"time"
)

func main() {
	addr := ":" + env("FLOW_WEB_PORT", "8080")
	backend := env("FLOW_BACKEND_URL", "http://127.0.0.1:7860")

	h, err := newHandler(backend)
	if err != nil {
		log.Fatalf("flowweb: %v", err)
	}
	srv := &http.Server{
		Addr:              addr,
		Handler:           h,
		ReadHeaderTimeout: 15 * time.Second,
	}
	log.Printf("flowweb: embedded UI on %s, API → %s", addr, backend)
	log.Fatal(srv.ListenAndServe())
}

func env(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}
