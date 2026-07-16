//! Contract proofs for `flow-core`, mirroring the Go `flow_test.go`: a domain-agnostic
//! pipeline runs in order, port types are checked at wire time, `ANY_TYPE` bypasses,
//! cycles are caught by `validate`, and `Mode` selects the backend over one scheduler.

use std::any::Any;
use std::collections::HashMap;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use flow_core::*;

// A domain supplies its own Value type — the engine is agnostic. `Text` stands in for
// a Message / Tensor / connector payload.
#[derive(Debug)]
struct Text(String);
impl Value for Text {
    fn port_type(&self) -> &str {
        "text"
    }
    fn as_any(&self) -> &dyn Any {
        self
    }
}
fn text(s: &str) -> ValueRef {
    Arc::new(Text(s.to_string()))
}
fn as_text(v: &ValueRef) -> &str {
    &v.as_any().downcast_ref::<Text>().expect("Text").0
}

struct Source {
    id: String,
    v: String,
}
impl Step for Source {
    fn id(&self) -> &str {
        &self.id
    }
    fn ins(&self) -> Vec<Port> {
        vec![]
    }
    fn outs(&self) -> Vec<Port> {
        vec![Port::new("out", "text")]
    }
    fn run(&self, _in: &Inputs) -> Result<Outputs, FlowError> {
        Ok(HashMap::from([("out".to_string(), text(&self.v))]))
    }
}

struct Upper {
    id: String,
}
impl Step for Upper {
    fn id(&self) -> &str {
        &self.id
    }
    fn ins(&self) -> Vec<Port> {
        vec![Port::new("in", "text")]
    }
    fn outs(&self) -> Vec<Port> {
        vec![Port::new("out", "text")]
    }
    fn run(&self, inp: &Inputs) -> Result<Outputs, FlowError> {
        let up = as_text(inp.get("in").expect("in")).to_uppercase();
        Ok(HashMap::from([("out".to_string(), text(&up))]))
    }
}

struct WantNumber {
    id: String,
}
impl Step for WantNumber {
    fn id(&self) -> &str {
        &self.id
    }
    fn ins(&self) -> Vec<Port> {
        vec![Port::new("in", "number")]
    }
    fn outs(&self) -> Vec<Port> {
        vec![]
    }
    fn run(&self, _in: &Inputs) -> Result<Outputs, FlowError> {
        Ok(HashMap::new())
    }
}

struct Passthrough {
    id: String,
}
impl Step for Passthrough {
    fn id(&self) -> &str {
        &self.id
    }
    fn ins(&self) -> Vec<Port> {
        vec![Port::new("in", ANY_TYPE)]
    }
    fn outs(&self) -> Vec<Port> {
        vec![Port::new("out", ANY_TYPE)]
    }
    fn run(&self, inp: &Inputs) -> Result<Outputs, FlowError> {
        let mut o = HashMap::new();
        if let Some(v) = inp.get("in") {
            o.insert("out".to_string(), v.clone());
        }
        Ok(o)
    }
}

// The P0: two steps wired output->input run in dependency order and only the terminal
// output is returned — one scheduler drives a domain-agnostic graph.
#[test]
fn pipeline_runs_in_process() {
    let mut g = Graph::new();
    g.add(Arc::new(Source { id: "src".into(), v: "hello".into() })).unwrap();
    g.add(Arc::new(Upper { id: "up".into() })).unwrap();
    g.wire(PortRef::new("src", "out"), PortRef::new("up", "in")).unwrap();

    let out = Scheduler::new().run(&g, Mode::InProcess, &HashMap::new()).unwrap();
    assert_eq!(as_text(out.get("up.out").expect("leaf")), "HELLO");
    assert!(!out.contains_key("src.out"), "non-terminal port leaked");
}

#[test]
fn wire_type_mismatch_rejected() {
    let mut g = Graph::new();
    g.add(Arc::new(Source { id: "src".into(), v: "x".into() })).unwrap();
    g.add(Arc::new(WantNumber { id: "n".into() })).unwrap();
    assert!(g.wire(PortRef::new("src", "out"), PortRef::new("n", "in")).is_err());
}

#[test]
fn any_type_bypasses_typecheck() {
    let mut g = Graph::new();
    g.add(Arc::new(Source { id: "src".into(), v: "x".into() })).unwrap();
    g.add(Arc::new(Passthrough { id: "p".into() })).unwrap();
    assert!(g.wire(PortRef::new("src", "out"), PortRef::new("p", "in")).is_ok());
}

#[test]
fn validate_rejects_cycle() {
    let mut g = Graph::new();
    g.add(Arc::new(Passthrough { id: "a".into() })).unwrap();
    g.add(Arc::new(Passthrough { id: "b".into() })).unwrap();
    g.wire(PortRef::new("a", "out"), PortRef::new("b", "in")).unwrap();
    g.wire(PortRef::new("b", "out"), PortRef::new("a", "in")).unwrap();
    assert!(g.validate().is_err());
}

// A backend for a mode is invoked, proving Mode is just backend selection over the
// identical scheduler walk. A real GpuResident/Durable backend would pin VRAM /
// checkpoint; the shape is identical.
struct Counting {
    calls: Arc<AtomicUsize>,
}
impl Backend for Counting {
    fn mode(&self) -> Mode {
        Mode::Durable
    }
    fn exec(&self, step: &dyn Step, inputs: &Inputs) -> Result<Outputs, FlowError> {
        self.calls.fetch_add(1, Ordering::SeqCst);
        step.run(inputs)
    }
}

#[test]
fn mode_selects_backend() {
    let mut g = Graph::new();
    g.add(Arc::new(Source { id: "src".into(), v: "hi".into() })).unwrap();

    let calls = Arc::new(AtomicUsize::new(0));
    let sched = Scheduler::new().with_backend(Box::new(Counting { calls: calls.clone() }));
    let out = sched.run(&g, Mode::Durable, &HashMap::new()).unwrap();

    assert_eq!(calls.load(Ordering::SeqCst), 1, "durable backend must run the step");
    assert_eq!(as_text(out.get("src.out").expect("out")), "hi");
}
