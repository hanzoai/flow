//! The `Durable` backend — checkpoint-and-resume, the seam under "build/test locally,
//! save to cloud, re-run / schedule on GPU."
//!
//! Each step's outputs are checkpointed to a [`Store`]; a step that already completed is
//! not re-executed — its checkpoint is returned. So a run survives a crash, resumes
//! where it stopped, and the same graph can be scheduled or re-run in the cloud without
//! repeating finished work.
//!
//! The core stays dependency-free: [`Store`] is a trait. hanzo cloud implements it over
//! S3 / Base; hanzo-desktop over local disk. The store trades in [`Outputs`] — an
//! `Arc`-shared value map — so an in-process store is a cheap refcount clone and a
//! persistent store serializes on its own terms, behind the seam.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use crate::{Backend, FlowError, Inputs, Mode, Outputs, Step};

/// A checkpoint store — the seam hanzo cloud (S3 / Base) and hanzo-desktop (local disk)
/// implement. Keyed by step id: holds a completed step's outputs so a run can resume
/// without re-executing it. Keying by id resumes one logical run; a memoizing store may
/// fold an input digest into the key to reuse results across runs.
pub trait Store: Send + Sync {
    /// A completed step's checkpointed outputs, or `None` if it hasn't run yet.
    fn load(&self, step_id: &str) -> Option<Outputs>;
    /// Record a step's outputs as its checkpoint.
    fn save(&self, step_id: &str, outputs: &Outputs);
}

/// An in-process checkpoint store — the reference [`Store`]. Proves the resume contract
/// and is genuinely useful for a single-process durable run (retry a failed graph
/// without repeating finished steps). Persistent stores implement the same trait.
#[derive(Default)]
pub struct MemoryStore {
    checkpoints: Mutex<HashMap<String, Outputs>>,
}

impl MemoryStore {
    pub fn new() -> Arc<Self> {
        Arc::new(Self::default())
    }
    /// How many steps have been checkpointed — lets a caller observe resume progress.
    pub fn len(&self) -> usize {
        self.checkpoints.lock().expect("store").len()
    }
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

impl Store for MemoryStore {
    fn load(&self, step_id: &str) -> Option<Outputs> {
        // Arc-shared values → cloning the map is a refcount bump, not a data copy.
        self.checkpoints.lock().expect("store").get(step_id).cloned()
    }
    fn save(&self, step_id: &str, outputs: &Outputs) {
        self.checkpoints.lock().expect("store").insert(step_id.to_string(), outputs.clone());
    }
}

/// The `Durable` backend: checkpoints each step to a [`Store`] and skips steps that
/// already completed, so a run resumes after a crash and can be scheduled / re-run in
/// the cloud. Register it on a [`crate::Scheduler`] and run a graph in [`Mode::Durable`].
pub struct DurableBackend {
    store: Arc<dyn Store>,
}

impl DurableBackend {
    pub fn new(store: Arc<dyn Store>) -> Self {
        Self { store }
    }
    pub fn store(&self) -> &Arc<dyn Store> {
        &self.store
    }
}

impl Backend for DurableBackend {
    fn mode(&self) -> Mode {
        Mode::Durable
    }

    fn exec(&self, step: &dyn Step, inputs: &Inputs) -> Result<Outputs, FlowError> {
        // Resume: a completed step is not re-run — return its checkpoint.
        if let Some(done) = self.store.load(step.id()) {
            return Ok(done);
        }
        let out = step.run(inputs)?;
        self.store.save(step.id(), &out);
        Ok(out)
    }
}
