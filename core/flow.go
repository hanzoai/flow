package flow

import (
	"context"
	"fmt"
)

// Value is an opaque typed value that travels along an edge. The engine never
// inspects it; the receiving Step interprets it per its domain. PortType is the
// tag the scheduler matches against a port's Type — the ONLY thing the engine
// reads about a value.
type Value interface {
	PortType() string
}

// Port is a typed input or output slot on a Step. Two ports connect only when
// their Type tags are equal (or one side is AnyType).
type Port struct {
	Name string
	Type string
}

// AnyType on either side of a wire disables the port type-check for that edge —
// the escape hatch for a genuinely polymorphic step (a pass-through, a fan-in).
const AnyType = "*"

// Inputs/Outputs carry a step's values keyed by port name.
type (
	Inputs  = map[string]Value
	Outputs = map[string]Value
)

// Step is one node: typed input ports, typed output ports, and a Run that maps
// inputs to outputs. Domains (LLM, tensor, connector, trigger) supply Steps; the
// engine only schedules them. Run must be pure w.r.t. the graph — its only inputs
// are `in` and ctx, its only outputs are the returned map and error. A Backend may
// wrap Run (to pin VRAM, or to checkpoint for durability) — the Step is unaware.
type Step interface {
	ID() string
	Ins() []Port
	Outs() []Port
	Run(ctx context.Context, in Inputs) (Outputs, error)
}

// PortRef names one port on one step.
type PortRef struct {
	Step string
	Port string
}

// Edge wires an upstream output port to a downstream input port.
type Edge struct {
	From PortRef // an Out port of From.Step
	To   PortRef // an In port of To.Step
}

// Graph is a DAG of steps wired output-port -> input-port. Build it with Add +
// Wire, then Validate (port types + acyclicity) before handing it to a Scheduler.
type Graph struct {
	steps map[string]Step
	edges []Edge
}

// NewGraph returns an empty graph.
func NewGraph() *Graph { return &Graph{steps: map[string]Step{}} }

// Add registers a step. A duplicate ID is an error — IDs are the graph's identity.
func (g *Graph) Add(s Step) error {
	id := s.ID()
	if id == "" {
		return fmt.Errorf("flow: step has empty ID")
	}
	if _, dup := g.steps[id]; dup {
		return fmt.Errorf("flow: duplicate step ID %q", id)
	}
	g.steps[id] = s
	return nil
}

// Wire connects an output port to an input port. Both endpoints must exist and
// their port Types must be compatible (equal, or one side AnyType).
func (g *Graph) Wire(from, to PortRef) error {
	out, err := g.port(from, false)
	if err != nil {
		return err
	}
	in, err := g.port(to, true)
	if err != nil {
		return err
	}
	if !typesMatch(out.Type, in.Type) {
		return fmt.Errorf("flow: type mismatch wiring %s.%s (%s) -> %s.%s (%s)",
			from.Step, from.Port, out.Type, to.Step, to.Port, in.Type)
	}
	g.edges = append(g.edges, Edge{From: from, To: to})
	return nil
}

// Validate checks that every wired port exists and the graph is acyclic. A future
// GPUResident/streaming mode may permit cycles; the base contract requires a DAG.
func (g *Graph) Validate() error {
	for _, e := range g.edges {
		if _, err := g.port(e.From, false); err != nil {
			return err
		}
		if _, err := g.port(e.To, true); err != nil {
			return err
		}
	}
	if _, err := g.topoOrder(); err != nil {
		return err
	}
	return nil
}

func typesMatch(a, b string) bool { return a == b || a == AnyType || b == AnyType }

// port resolves a PortRef to its Port, checking side (in vs out).
func (g *Graph) port(r PortRef, input bool) (Port, error) {
	s, ok := g.steps[r.Step]
	if !ok {
		return Port{}, fmt.Errorf("flow: no step %q", r.Step)
	}
	ports := s.Outs()
	side := "output"
	if input {
		ports, side = s.Ins(), "input"
	}
	for _, p := range ports {
		if p.Name == r.Port {
			return p, nil
		}
	}
	return Port{}, fmt.Errorf("flow: step %q has no %s port %q", r.Step, side, r.Port)
}

// topoOrder returns step IDs in dependency order (an edge From->To means From
// runs before To), or an error naming the cycle. Kahn's algorithm — deterministic
// by sorted ID so a graph always schedules the same way.
func (g *Graph) topoOrder() ([]string, error) {
	indeg := make(map[string]int, len(g.steps))
	for id := range g.steps {
		indeg[id] = 0
	}
	succ := make(map[string][]string, len(g.steps))
	for _, e := range g.edges {
		succ[e.From.Step] = append(succ[e.From.Step], e.To.Step)
		indeg[e.To.Step]++
	}
	ready := sortedZero(indeg)
	order := make([]string, 0, len(g.steps))
	for len(ready) > 0 {
		id := ready[0]
		ready = ready[1:]
		order = append(order, id)
		for _, n := range succ[id] {
			indeg[n]--
			if indeg[n] == 0 {
				ready = insertSorted(ready, n)
			}
		}
	}
	if len(order) != len(g.steps) {
		return nil, fmt.Errorf("flow: graph has a cycle (%d of %d steps scheduled)", len(order), len(g.steps))
	}
	return order, nil
}
