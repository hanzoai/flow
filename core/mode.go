package flow

import "context"

// Mode is a graph's execution locality and durability. It is a PARAMETER of a run,
// not a property of the engine — the single most important decomplection here.
// The scheduler is identical across modes; Mode only selects the Backend that
// realizes step execution and value hand-off.
type Mode int

const (
	// InProcess: steps run in-process, values passed by reference in shared memory,
	// nothing serialized, no crash-resume. The default for LLM/agent chains.
	InProcess Mode = iota

	// GPUResident: values (tensors/latents) stay pinned in device memory between
	// steps and are never serialized to disk. The mode that keeps a diffusion
	// pipeline fast — a Durable backend applied here would serialize a latent per
	// node and destroy throughput, which is exactly why Mode is a parameter.
	GPUResident

	// Durable: every step is checkpointed so a run resumes after a crash; the
	// backend dispatches steps as activities on the durable workflow engine
	// (hanzoai/tasks). The mode that makes a triggered automation reliable.
	Durable
)

func (m Mode) String() string {
	switch m {
	case InProcess:
		return "in-process"
	case GPUResident:
		return "gpu-resident"
	case Durable:
		return "durable"
	default:
		return "mode(?)"
	}
}

// Backend realizes a Step's execution for one Mode. It is the seam where locality
// and durability live: an InProcess backend just calls Step.Run; a GPUResident
// backend pins device memory and reuses it across steps; a Durable backend records
// the step as a checkpointed activity and replays on resume. A Backend holds NO
// graph knowledge — the one Scheduler owns topology; a Backend owns only "how does
// a single step actually run in this mode."
type Backend interface {
	Mode() Mode
	Exec(ctx context.Context, s Step, in Inputs) (Outputs, error)
}
