//! `flow-core` — the ONE step-DAG engine, Rust core.
//!
//! There is exactly one scheduler. Everything — LLM chains, media/diffusion
//! pipelines, IFTTT automations, agent tool-graphs — is this engine applied to two
//! parameters:
//!
//! - **Value type** — what travels on an edge (a Message, a Tensor, connector I/O).
//!   The engine never inspects it; a [`Step`] interprets it per its domain. Values
//!   are `Arc<dyn Value>` so they pass **zero-copy** between steps — the point for
//!   tensors on a GPU.
//! - **[`Mode`]** — execution locality/durability (`InProcess | GpuResident |
//!   Durable`). A *parameter*, never baked in: a media flow keeps latents pinned in
//!   VRAM and serializes nothing; an automation checkpoints every step. Same
//!   scheduler, different [`Backend`].
//!
//! The crate is dependency-free and holds no domain knowledge, so it is a small,
//! embeddable library: the *same* engine runs in hanzo-desktop (local/private,
//! low-memory) and the cloud, with GPU compute (hanzo-ml / hanzo-fusion on
//! hanzo-engine) plugged in as a [`Backend`], not a core dependency. It mirrors the
//! Go `hanzoai/flow/core` contract 1:1 so the two stay in lockstep.

use std::any::Any;
use std::collections::{BTreeSet, HashMap};
use std::fmt;
use std::sync::Arc;

/// The `GpuResident` backend + `Device` seam (hanzo-ml / hanzo-fusion on hanzo-engine).
pub mod gpu;

// ── Errors ───────────────────────────────────────────────────────────────────

/// Every fallible engine operation returns this. Variants name the exact defect so
/// a malformed graph fails loudly before any step executes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FlowError {
    EmptyStepId,
    DuplicateStep(String),
    NoStep(String),
    NoPort { step: String, side: &'static str, port: String },
    TypeMismatch { from: String, from_ty: String, to: String, to_ty: String },
    Cycle { scheduled: usize, total: usize },
    NoBackend(Mode),
    Step { id: String, source: String },
}

impl fmt::Display for FlowError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            FlowError::EmptyStepId => write!(f, "flow: step has empty id"),
            FlowError::DuplicateStep(id) => write!(f, "flow: duplicate step id {id:?}"),
            FlowError::NoStep(id) => write!(f, "flow: no step {id:?}"),
            FlowError::NoPort { step, side, port } => {
                write!(f, "flow: step {step:?} has no {side} port {port:?}")
            }
            FlowError::TypeMismatch { from, from_ty, to, to_ty } => write!(
                f,
                "flow: type mismatch wiring {from} ({from_ty}) -> {to} ({to_ty})"
            ),
            FlowError::Cycle { scheduled, total } => {
                write!(f, "flow: graph has a cycle ({scheduled} of {total} steps scheduled)")
            }
            FlowError::NoBackend(m) => write!(f, "flow: no backend for {m}"),
            FlowError::Step { id, source } => write!(f, "flow: step {id:?}: {source}"),
        }
    }
}

impl std::error::Error for FlowError {}

// ── Value + Port ──────────────────────────────────────────────────────────────

/// An opaque typed value on an edge. The engine reads only [`Value::port_type`]; a
/// [`Step`] downcasts via [`Value::as_any`] to its own domain type. Held behind
/// `Arc` so hand-off between steps is a refcount bump, not a copy.
pub trait Value: Send + Sync {
    /// The port type tag the scheduler matches on.
    fn port_type(&self) -> &str;
    /// Downcast hook so a step recovers its concrete value type.
    fn as_any(&self) -> &dyn Any;
}

/// A reference-counted value flowing on an edge.
pub type ValueRef = Arc<dyn Value>;

/// On either side of a wire, disables the port type-check for that edge — the escape
/// hatch for a genuinely polymorphic step (a pass-through, a fan-in).
pub const ANY_TYPE: &str = "*";

/// A typed input or output slot on a [`Step`].
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Port {
    pub name: String,
    pub ty: String,
}

impl Port {
    pub fn new(name: impl Into<String>, ty: impl Into<String>) -> Self {
        Self { name: name.into(), ty: ty.into() }
    }
}

fn types_match(a: &str, b: &str) -> bool {
    a == b || a == ANY_TYPE || b == ANY_TYPE
}

// ── Step ──────────────────────────────────────────────────────────────────────

/// A step's values, keyed by port name.
pub type Inputs = HashMap<String, ValueRef>;
/// A step's produced values, keyed by port name.
pub type Outputs = HashMap<String, ValueRef>;

/// One node: typed input ports, typed output ports, and a `run` mapping inputs to
/// outputs. Domains (LLM, tensor, connector, trigger) supply steps; the engine only
/// schedules them. A [`Backend`] may *wrap* `run` (pin VRAM, checkpoint) — the step
/// is unaware.
pub trait Step: Send + Sync {
    fn id(&self) -> &str;
    fn ins(&self) -> Vec<Port>;
    fn outs(&self) -> Vec<Port>;
    fn run(&self, inputs: &Inputs) -> Result<Outputs, FlowError>;
}

/// Names one port on one step.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PortRef {
    pub step: String,
    pub port: String,
}

impl PortRef {
    pub fn new(step: impl Into<String>, port: impl Into<String>) -> Self {
        Self { step: step.into(), port: port.into() }
    }
    fn key(&self) -> String {
        format!("{}.{}", self.step, self.port)
    }
}

#[derive(Clone, Debug)]
struct Edge {
    from: PortRef,
    to: PortRef,
}

// ── Mode + Backend ──────────────────────────────────────────────────────────────

/// A graph's execution locality and durability — a *parameter* of a run, not a
/// property of the engine. The scheduler is identical across modes; `Mode` only
/// selects the [`Backend`].
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Mode {
    /// In-process, values shared by `Arc`, nothing serialized. The default.
    InProcess,
    /// Tensors/latents stay pinned in device memory between steps, never serialized —
    /// the mode that keeps a diffusion pipeline fast (hanzo-ml / hanzo-fusion).
    GpuResident,
    /// Every step is checkpointed so a run resumes after a crash (durable engine).
    Durable,
}

impl fmt::Display for Mode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Mode::InProcess => "in-process",
            Mode::GpuResident => "gpu-resident",
            Mode::Durable => "durable",
        })
    }
}

/// Realizes a [`Step`]'s execution for one [`Mode`] — the seam where locality and
/// durability live. Holds NO graph knowledge; the one [`Scheduler`] owns topology.
pub trait Backend: Send + Sync {
    fn mode(&self) -> Mode;
    fn exec(&self, step: &dyn Step, inputs: &Inputs) -> Result<Outputs, FlowError>;
}

/// The reference backend: runs a step by calling [`Step::run`] directly, values
/// shared in-process. `GpuResident` (hanzo-ml VRAM) and `Durable` (checkpointed)
/// backends register the same way.
pub struct InProcess;

impl Backend for InProcess {
    fn mode(&self) -> Mode {
        Mode::InProcess
    }
    fn exec(&self, step: &dyn Step, inputs: &Inputs) -> Result<Outputs, FlowError> {
        step.run(inputs)
    }
}

// ── Graph ───────────────────────────────────────────────────────────────────────

/// A DAG of steps wired output-port -> input-port. Build with [`Graph::add`] +
/// [`Graph::wire`], then [`Graph::validate`] before handing to a [`Scheduler`].
pub struct Graph {
    steps: HashMap<String, Arc<dyn Step>>,
    edges: Vec<Edge>,
}

impl Graph {
    pub fn new() -> Self {
        Self { steps: HashMap::new(), edges: Vec::new() }
    }

    /// Registers a step. A duplicate id is an error — ids are the graph's identity.
    pub fn add(&mut self, step: Arc<dyn Step>) -> Result<(), FlowError> {
        let id = step.id().to_string();
        if id.is_empty() {
            return Err(FlowError::EmptyStepId);
        }
        if self.steps.contains_key(&id) {
            return Err(FlowError::DuplicateStep(id));
        }
        self.steps.insert(id, step);
        Ok(())
    }

    /// Connects an output port to an input port; endpoints must exist and their port
    /// types must be compatible (equal, or one side [`ANY_TYPE`]).
    pub fn wire(&mut self, from: PortRef, to: PortRef) -> Result<(), FlowError> {
        let out = self.port(&from, false)?;
        let inp = self.port(&to, true)?;
        if !types_match(&out.ty, &inp.ty) {
            return Err(FlowError::TypeMismatch {
                from: from.key(),
                from_ty: out.ty,
                to: to.key(),
                to_ty: inp.ty,
            });
        }
        self.edges.push(Edge { from, to });
        Ok(())
    }

    /// Checks that every wired port exists and the graph is acyclic.
    pub fn validate(&self) -> Result<(), FlowError> {
        for e in &self.edges {
            self.port(&e.from, false)?;
            self.port(&e.to, true)?;
        }
        self.topo_order().map(|_| ())
    }

    fn port(&self, r: &PortRef, input: bool) -> Result<Port, FlowError> {
        let s = self.steps.get(&r.step).ok_or_else(|| FlowError::NoStep(r.step.clone()))?;
        let (ports, side) = if input { (s.ins(), "input") } else { (s.outs(), "output") };
        ports
            .into_iter()
            .find(|p| p.name == r.port)
            .ok_or_else(|| FlowError::NoPort {
                step: r.step.clone(),
                side,
                port: r.port.clone(),
            })
    }

    /// Step ids in dependency order (Kahn's algorithm, deterministic by sorted id so
    /// a graph always schedules the same way), or a cycle error.
    fn topo_order(&self) -> Result<Vec<String>, FlowError> {
        let mut indeg: HashMap<String, usize> = self.steps.keys().map(|k| (k.clone(), 0)).collect();
        let mut succ: HashMap<String, Vec<String>> = HashMap::new();
        for e in &self.edges {
            succ.entry(e.from.step.clone()).or_default().push(e.to.step.clone());
            if let Some(d) = indeg.get_mut(&e.to.step) {
                *d += 1;
            }
        }
        let mut ready: BTreeSet<String> =
            indeg.iter().filter(|(_, d)| **d == 0).map(|(k, _)| k.clone()).collect();
        let mut order = Vec::with_capacity(self.steps.len());
        while let Some(id) = ready.iter().next().cloned() {
            ready.remove(&id);
            order.push(id.clone());
            if let Some(ns) = succ.get(&id) {
                for n in ns {
                    if let Some(d) = indeg.get_mut(n) {
                        *d -= 1;
                        if *d == 0 {
                            ready.insert(n.clone());
                        }
                    }
                }
            }
        }
        if order.len() != self.steps.len() {
            return Err(FlowError::Cycle { scheduled: order.len(), total: self.steps.len() });
        }
        Ok(order)
    }
}

impl Default for Graph {
    fn default() -> Self {
        Self::new()
    }
}

// ── Scheduler ────────────────────────────────────────────────────────────────────

/// THE one scheduler. Runs any [`Graph`] in any [`Mode`] by delegating each step's
/// execution to the mode's [`Backend`]. The topology walk — dependency order,
/// gathering each step's inputs from upstream output ports, propagating outputs — is
/// identical for every mode and every value domain.
pub struct Scheduler {
    backends: HashMap<Mode, Box<dyn Backend>>,
}

impl Scheduler {
    /// A scheduler with the reference [`InProcess`] backend always available.
    pub fn new() -> Self {
        let mut backends: HashMap<Mode, Box<dyn Backend>> = HashMap::new();
        backends.insert(Mode::InProcess, Box::new(InProcess));
        Self { backends }
    }

    /// Registers a backend for its mode (builder-style).
    pub fn with_backend(mut self, b: Box<dyn Backend>) -> Self {
        self.backends.insert(b.mode(), b);
        self
    }

    /// Executes `g` in `mode` and returns the outputs of the graph's terminal steps
    /// (output ports feeding no edge), keyed `"stepId.portName"`. `source` supplies
    /// the graph's inputs for unwired input ports, keyed the same way. Validates
    /// first, so a malformed graph fails before any step runs.
    pub fn run(&self, g: &Graph, mode: Mode, source: &Inputs) -> Result<Outputs, FlowError> {
        let backend = self.backends.get(&mode).ok_or(FlowError::NoBackend(mode))?;
        g.validate()?;
        let order = g.topo_order()?;

        // wires[to] = the upstream (from) that feeds input port `to`.
        let mut wires: HashMap<String, PortRef> = HashMap::new();
        let mut fed: BTreeSet<String> = BTreeSet::new();
        for e in &g.edges {
            wires.insert(e.to.key(), e.from.clone());
            fed.insert(e.from.key());
        }

        // produced["stepId.port"] = value emitted by that output port.
        let mut produced: HashMap<String, ValueRef> = HashMap::new();
        for id in &order {
            let step = g.steps.get(id).expect("id from topo_order");
            let mut step_in: Inputs = HashMap::new();
            for p in step.ins() {
                let r = PortRef::new(id.clone(), p.name.clone());
                if let Some(up) = wires.get(&r.key()) {
                    if let Some(v) = produced.get(&up.key()) {
                        step_in.insert(p.name.clone(), v.clone());
                    }
                } else if let Some(v) = source.get(&r.key()) {
                    step_in.insert(p.name.clone(), v.clone());
                }
            }
            let out = backend
                .exec(step.as_ref(), &step_in)
                .map_err(|e| FlowError::Step { id: id.clone(), source: e.to_string() })?;
            for p in step.outs() {
                if let Some(v) = out.get(&p.name) {
                    produced.insert(PortRef::new(id.clone(), p.name).key(), v.clone());
                }
            }
        }

        // Result = every produced output port that feeds no downstream edge (leaves).
        let mut result: Outputs = HashMap::new();
        for id in &order {
            for p in g.steps.get(id).expect("id from topo_order").outs() {
                let r = PortRef::new(id.clone(), p.name);
                if !fed.contains(&r.key()) {
                    if let Some(v) = produced.get(&r.key()) {
                        result.insert(r.key(), v.clone());
                    }
                }
            }
        }
        Ok(result)
    }
}

impl Default for Scheduler {
    fn default() -> Self {
        Self::new()
    }
}
