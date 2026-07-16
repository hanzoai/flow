package flow

import (
	"context"
	"fmt"
	"sort"
)

// Scheduler is THE one scheduler. It runs any Graph in any Mode by delegating each
// step's execution to the Mode's Backend. The topology walk — dependency order,
// gathering each step's inputs from upstream output ports, propagating outputs — is
// identical for every mode and every value domain. That single walk, curried over
// (value-domain, Mode), is the whole platform's execution model.
type Scheduler struct {
	backends map[Mode]Backend
}

// New builds a scheduler over the given backends (one per Mode). InProcess is
// always available as a fallback so a scheduler is never empty.
func New(backends ...Backend) *Scheduler {
	s := &Scheduler{backends: map[Mode]Backend{InProcess: inProcess{}}}
	for _, b := range backends {
		s.backends[b.Mode()] = b
	}
	return s
}

// Run executes g in the given mode and returns the outputs of the graph's terminal
// steps (steps whose output ports feed no edge), keyed "stepID.portName". The
// caller supplies the graph's source inputs keyed the same way for unwired input
// ports. Run validates first, so a malformed graph fails before any step executes.
func (s *Scheduler) Run(ctx context.Context, g *Graph, mode Mode, in map[string]Value) (map[string]Value, error) {
	backend, ok := s.backends[mode]
	if !ok {
		return nil, fmt.Errorf("flow: no backend for %s", mode)
	}
	if err := g.Validate(); err != nil {
		return nil, err
	}
	order, err := g.topoOrder()
	if err != nil {
		return nil, err
	}

	// wires[to] = the upstream (from) that feeds input port `to`.
	wires := make(map[PortRef]PortRef, len(g.edges))
	fed := make(map[PortRef]bool, len(g.edges)) // output ports that feed some edge
	for _, e := range g.edges {
		wires[e.To] = e.From
		fed[e.From] = true
	}

	// produced[stepID.port] = value emitted by that output port.
	produced := make(map[string]Value)
	for _, id := range order {
		step := g.steps[id]
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		stepIn := make(Inputs, len(step.Ins()))
		for _, p := range step.Ins() {
			ref := PortRef{Step: id, Port: p.Name}
			if up, wired := wires[ref]; wired {
				stepIn[p.Name] = produced[key(up)]
			} else if v, ok := in[key(ref)]; ok {
				stepIn[p.Name] = v // graph source input
			}
		}
		out, err := backend.Exec(ctx, step, stepIn)
		if err != nil {
			return nil, fmt.Errorf("flow: step %q: %w", id, err)
		}
		for _, p := range step.Outs() {
			if v, ok := out[p.Name]; ok {
				produced[key(PortRef{Step: id, Port: p.Name})] = v
			}
		}
	}

	// Result = every produced output port that feeds no downstream edge (the leaves).
	result := make(map[string]Value)
	for _, id := range order {
		for _, p := range g.steps[id].Outs() {
			ref := PortRef{Step: id, Port: p.Name}
			if v, ok := produced[key(ref)]; ok && !fed[ref] {
				result[key(ref)] = v
			}
		}
	}
	return result, nil
}

func key(r PortRef) string { return r.Step + "." + r.Port }

// sortedZero returns the zero-indegree IDs in sorted order (deterministic scheduling).
func sortedZero(indeg map[string]int) []string {
	var z []string
	for id, d := range indeg {
		if d == 0 {
			z = append(z, id)
		}
	}
	sort.Strings(z)
	return z
}

// insertSorted keeps the ready queue sorted so topological order is deterministic.
func insertSorted(q []string, id string) []string {
	i := sort.SearchStrings(q, id)
	q = append(q, "")
	copy(q[i+1:], q[i:])
	q[i] = id
	return q
}
