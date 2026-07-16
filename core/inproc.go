package flow

import "context"

// inProcess is the reference Backend: it runs a step by calling Step.Run directly,
// values passed by reference in shared memory. No serialization, no checkpointing.
// It is always registered (New seeds it) so the engine works out of the box; the
// GPUResident and Durable backends live in their own packages (studio's VRAM
// executor, auto/tasks' activity dispatcher) and register the same way.
type inProcess struct{}

func (inProcess) Mode() Mode { return InProcess }

func (inProcess) Exec(ctx context.Context, s Step, in Inputs) (Outputs, error) {
	return s.Run(ctx, in)
}
