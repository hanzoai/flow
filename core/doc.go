// Package flow is the ONE step-DAG engine the whole platform composes on.
//
// There is exactly one scheduler. Everything — LLM chains, media/diffusion
// pipelines, IFTTT automations, agent tool-graphs — is this engine applied to
// two parameters:
//
//	Value type  — what travels on an edge (a Message, a Tensor, connector I/O).
//	              The engine NEVER inspects it; a Step interprets it per its domain.
//	Mode        — execution locality/durability (InProcess | GPUResident | Durable).
//	              A PARAMETER, never baked in: a media flow keeps latents pinned in
//	              VRAM and serializes nothing; an automation checkpoints every step
//	              on the durable backend. Same scheduler, different Backend.
//
// So a product is just flow curried:
//
//	studio      = Run(GPUResident, Graph-of-Tensor-steps)   // comfy nodes
//	automations = Run(Durable,     Graph-of-ConnectorIO)    // triggers -> actions
//	llmFlow     = Run(InProcess,   Graph-of-Message-steps)  // flow (lfx) nodes
//
// A domain supplies Steps (typed input ports -> typed output ports + a Run fn) and,
// if it has special execution needs, a Backend for a Mode. The engine only wires
// matching ports and schedules them. This package is stdlib-only and holds no
// domain knowledge — it is the seam every node-pack and every execution backend
// plugs into.
package flow
