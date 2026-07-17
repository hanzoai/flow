//! Proves the `Durable` backend contract: a step's outputs are checkpointed, and on a
//! resume (same store) a completed step is NOT re-executed — its checkpoint is returned.
//! That's what lets a run survive a crash and be re-run / scheduled in the cloud without
//! repeating finished work. A `MemoryStore` stands in for the cloud S3/Base store.

use std::any::Any;
use std::collections::HashMap;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use flow_core::durable::{DurableBackend, MemoryStore, Store};
use flow_core::*;

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
fn as_text(v: &ValueRef) -> &str {
    &v.as_any().downcast_ref::<Text>().expect("Text").0
}

// Counts how many times it actually executes, so a test can assert a resumed step is
// served from the checkpoint instead of re-running.
struct CountingSource {
    id: String,
    runs: Arc<AtomicUsize>,
}
impl Step for CountingSource {
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
        self.runs.fetch_add(1, Ordering::SeqCst);
        Ok(HashMap::from([("out".to_string(), Arc::new(Text("computed".into())) as ValueRef)]))
    }
}

fn run_once(store: Arc<dyn Store>, runs: Arc<AtomicUsize>) -> String {
    let mut g = Graph::new();
    g.add(Arc::new(CountingSource { id: "src".into(), runs })).unwrap();
    let sched = Scheduler::new().with_backend(Box::new(DurableBackend::new(store)));
    let out = sched.run(&g, Mode::Durable, &HashMap::new()).unwrap();
    as_text(out.get("src.out").expect("out")).to_string()
}

#[test]
fn resume_skips_completed_steps() {
    let store = MemoryStore::new();
    let runs = Arc::new(AtomicUsize::new(0));

    // First run: the step executes and is checkpointed.
    let first = run_once(store.clone(), runs.clone());
    assert_eq!(first, "computed");
    assert_eq!(runs.load(Ordering::SeqCst), 1, "step runs once on the first pass");
    assert_eq!(store.len(), 1, "step got checkpointed");

    // Resume against the same store: the step is served from its checkpoint, not re-run.
    let second = run_once(store.clone(), runs.clone());
    assert_eq!(second, "computed", "resume returns the checkpointed output");
    assert_eq!(runs.load(Ordering::SeqCst), 1, "resumed step was NOT re-executed");
}

#[test]
fn fresh_store_runs_the_step() {
    // A different store has no checkpoint, so the step runs again — proving the skip is
    // driven by the store's contents, not a global flag.
    let runs = Arc::new(AtomicUsize::new(0));
    run_once(MemoryStore::new(), runs.clone());
    run_once(MemoryStore::new(), runs.clone());
    assert_eq!(runs.load(Ordering::SeqCst), 2, "each fresh store re-runs the step");
}

#[test]
fn durable_backend_reports_its_mode() {
    let store = MemoryStore::new();
    let b = DurableBackend::new(store.clone());
    assert_eq!(b.mode(), Mode::Durable);
    assert!(b.store().load("nope").is_none());
    assert!(store.is_empty());
}
