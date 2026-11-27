# Hanzo Flow Go SDK

Zero-dependency Go client for the canonical **Hanzo Flow** REST API (`/v1/flow/*`), built exclusively on the Go standard library (`net/http`).

## Install

```bash
go get github.com/hanzoai/flow/sdk/go
```

## Usage

```go
package main

import (
	"context"
	"fmt"
	"log"
	"os"

	flow "github.com/hanzoai/flow/sdk/go"
)

func main() {
	client := flow.NewClient(
		flow.WithToken(os.Getenv("HANZO_API_KEY")),
		flow.WithOrgID("hanzo"),
	)

	ctx := context.Background()
	st, err := client.Status(ctx)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("reachable=%v version=%s\n", st.Reachable, st.Version)

	graph := flow.NewWorkflowGraph()
	wf, err := client.CreateWorkflow(ctx, flow.CreateWorkflowRequest{
		Name:        "support-triage",
		Description: "Route incoming tickets",
		Data:        &graph,
	})
	if err != nil {
		log.Fatal(err)
	}

	res, err := client.Run(ctx, flow.RunRequest{
		Workflow: wf.ID,
		Input:    "Summarize today's tickets",
	})
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("session:", res.SessionID)
}
```

## Test

```bash
GOWORK=off go vet ./...
GOWORK=off go test -race -count=1 ./...
```
