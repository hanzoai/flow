package flow

import (
	"context"
	"strings"
	"testing"
)

// A domain supplies its own Value type — the engine is agnostic to it. Here a
// trivial "text" value stands in for a Message/Tensor/connector payload.
type text string

func (text) PortType() string { return "text" }

// source emits a fixed text on port "out".
type source struct {
	id string
	v  text
}

func (s source) ID() string    { return s.id }
func (s source) Ins() []Port   { return nil }
func (s source) Outs() []Port  { return []Port{{Name: "out", Type: "text"}} }
func (s source) Run(_ context.Context, _ Inputs) (Outputs, error) {
	return Outputs{"out": s.v}, nil
}

// upper reads port "in" and emits its upper-cased text on port "out".
type upper struct{ id string }

func (u upper) ID() string   { return u.id }
func (u upper) Ins() []Port  { return []Port{{Name: "in", Type: "text"}} }
func (u upper) Outs() []Port { return []Port{{Name: "out", Type: "text"}} }
func (u upper) Run(_ context.Context, in Inputs) (Outputs, error) {
	return Outputs{"out": text(strings.ToUpper(string(in["in"].(text))))}, nil
}

// wantNumber declares an input port of a DIFFERENT type, to exercise the wire typecheck.
type wantNumber struct{ id string }

func (w wantNumber) ID() string   { return w.id }
func (w wantNumber) Ins() []Port  { return []Port{{Name: "in", Type: "number"}} }
func (w wantNumber) Outs() []Port { return nil }
func (w wantNumber) Run(context.Context, Inputs) (Outputs, error) { return nil, nil }

// TestPipeline_RunsInProcess is the P0: two steps wired output->input run in
// dependency order and the terminal step's output is returned — proving the ONE
// scheduler drives a domain-agnostic graph with the reference backend.
func TestPipeline_RunsInProcess(t *testing.T) {
	g := NewGraph()
	if err := g.Add(source{id: "src", v: "hello"}); err != nil {
		t.Fatal(err)
	}
	if err := g.Add(upper{id: "up"}); err != nil {
		t.Fatal(err)
	}
	if err := g.Wire(PortRef{"src", "out"}, PortRef{"up", "in"}); err != nil {
		t.Fatalf("wire: %v", err)
	}

	out, err := New().Run(context.Background(), g, InProcess, nil)
	if err != nil {
		t.Fatalf("run: %v", err)
	}
	// "up.out" is the only leaf (src.out feeds up, so it's not terminal).
	if got, ok := out["up.out"].(text); !ok || got != "HELLO" {
		t.Fatalf("leaf output = %v, want up.out=HELLO", out)
	}
	if _, leaked := out["src.out"]; leaked {
		t.Fatalf("non-terminal port src.out leaked into result: %v", out)
	}
}

// TestWire_TypeMismatchRejected: wiring text -> number fails at Wire, before any run.
func TestWire_TypeMismatchRejected(t *testing.T) {
	g := NewGraph()
	_ = g.Add(source{id: "src", v: "x"})
	_ = g.Add(wantNumber{id: "n"})
	if err := g.Wire(PortRef{"src", "out"}, PortRef{"n", "in"}); err == nil {
		t.Fatal("expected type-mismatch error wiring text(out) -> number(in)")
	}
}

// TestAnyType_BypassesTypecheck: an AnyType port connects to anything.
func TestAnyType_BypassesTypecheck(t *testing.T) {
	g := NewGraph()
	_ = g.Add(source{id: "src", v: "x"})
	_ = g.Add(passthrough{id: "p"})
	if err := g.Wire(PortRef{"src", "out"}, PortRef{"p", "in"}); err != nil {
		t.Fatalf("AnyType input should accept text: %v", err)
	}
}

type passthrough struct{ id string }

func (p passthrough) ID() string   { return p.id }
func (p passthrough) Ins() []Port  { return []Port{{Name: "in", Type: AnyType}} }
func (p passthrough) Outs() []Port { return []Port{{Name: "out", Type: AnyType}} }
func (p passthrough) Run(_ context.Context, in Inputs) (Outputs, error) {
	return Outputs{"out": in["in"]}, nil
}

// TestValidate_RejectsCycle: a cycle is caught by Validate/topoOrder, not at runtime.
func TestValidate_RejectsCycle(t *testing.T) {
	g := NewGraph()
	_ = g.Add(passthrough{id: "a"})
	_ = g.Add(passthrough{id: "b"})
	_ = g.Wire(PortRef{"a", "out"}, PortRef{"b", "in"})
	_ = g.Wire(PortRef{"b", "out"}, PortRef{"a", "in"})
	if err := g.Validate(); err == nil {
		t.Fatal("expected cycle detection error")
	}
}

// TestRun_ModeSelectsBackend: a custom backend for a mode is invoked, proving Mode
// is just backend selection over the identical scheduler walk.
func TestRun_ModeSelectsBackend(t *testing.T) {
	g := NewGraph()
	_ = g.Add(source{id: "src", v: "hi"})

	spy := &countingBackend{mode: Durable}
	out, err := New(spy).Run(context.Background(), g, Durable, nil)
	if err != nil {
		t.Fatalf("run: %v", err)
	}
	if spy.calls != 1 {
		t.Fatalf("durable backend Exec called %d times, want 1", spy.calls)
	}
	if got := out["src.out"].(text); got != "hi" {
		t.Fatalf("output = %q, want hi", got)
	}
}

type countingBackend struct {
	mode  Mode
	calls int
}

func (c *countingBackend) Mode() Mode { return c.mode }
func (c *countingBackend) Exec(ctx context.Context, s Step, in Inputs) (Outputs, error) {
	c.calls++
	return s.Run(ctx, in) // a real durable backend would checkpoint; the shape is identical
}
