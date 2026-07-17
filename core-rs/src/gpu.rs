//! The `GpuResident` backend — the seam where `hanzo-ml` / `hanzo-fusion` (on
//! `hanzo-engine`) plug in.
//!
//! In this mode, tensor values stay pinned in device memory across steps: a
//! [`DeviceTensor`] carries only an opaque device handle, never the bytes, so passing
//! it between steps is a refcount bump and it never round-trips through host memory.
//! That's what keeps a diffusion pipeline fast.
//!
//! The core stays dependency-free: it defines the [`Device`] trait and injects the
//! active device into steps via [`current_device`] during a run. A real backend
//! implements [`Device`] over `hanzo-ml` (CUDA / Metal / WGSL kernels); GPU steps pull
//! the device from the context and dispatch their kernels. Nothing here needs a GPU or
//! `hanzo-ml` to compile or to prove the contract — a stub device stands in for tests.

use std::any::Any;
use std::cell::RefCell;
use std::sync::Arc;

use crate::{Backend, FlowError, Inputs, Mode, Outputs, Step, Value};

/// A compute device — the seam `hanzo-ml` / `hanzo-fusion` implement. The core knows
/// only that a device has a name and hosts resident tensors; the actual kernels
/// (matmul, sample, VAE-decode, …) live in `hanzo-ml`, reached by GPU steps that pull
/// the device from [`current_device`].
pub trait Device: Send + Sync {
    /// A stable device identity, e.g. `"cuda:0"`, `"metal"`, `"cpu-fallback"`.
    fn name(&self) -> &str;
    /// Downcast hatch: a GPU step recovers its concrete device (the `hanzo-ml` handle)
    /// to call typed kernels — `current_device().and_then(|d| d.as_any().downcast_ref())`.
    /// Same pattern as [`Value::as_any`].
    fn as_any(&self) -> &dyn Any;
}

/// A tensor resident in device memory. It carries only an opaque `handle` (a
/// `hanzo-ml` tensor id / device pointer) — NEVER the bytes — so it flows between
/// steps zero-copy and is never serialized to host. This is the value on
/// `GpuResident` edges.
#[derive(Debug, Clone)]
pub struct DeviceTensor {
    pub device: String,
    pub handle: u64,
    pub shape: Vec<usize>,
    pub dtype: String,
}

impl Value for DeviceTensor {
    fn port_type(&self) -> &str {
        "tensor"
    }
    fn as_any(&self) -> &dyn Any {
        self
    }
}

thread_local! {
    /// The device the current `GpuResident` exec is running on. Set by
    /// [`GpuResidentBackend`] around each step, cleared after — so GPU steps read it
    /// via [`current_device`] without threading it through the [`Step`] signature.
    static ACTIVE_DEVICE: RefCell<Option<Arc<dyn Device>>> = const { RefCell::new(None) };
}

/// The device the current step is running on, or `None` outside a `GpuResident` run.
/// GPU steps call this in [`Step::run`] to reach the device for their kernels.
pub fn current_device() -> Option<Arc<dyn Device>> {
    ACTIVE_DEVICE.with(|d| d.borrow().clone())
}

/// The `GpuResident` backend: holds the device and runs each step with it injected via
/// [`current_device`], keeping tensor values device-resident between steps. Register it
/// on a [`crate::Scheduler`] and run a graph in [`Mode::GpuResident`].
pub struct GpuResidentBackend {
    device: Arc<dyn Device>,
}

impl GpuResidentBackend {
    pub fn new(device: Arc<dyn Device>) -> Self {
        Self { device }
    }
    pub fn device(&self) -> &Arc<dyn Device> {
        &self.device
    }
}

impl Backend for GpuResidentBackend {
    fn mode(&self) -> Mode {
        Mode::GpuResident
    }

    fn exec(&self, step: &dyn Step, inputs: &Inputs) -> Result<Outputs, FlowError> {
        // Inject the device for the duration of this step, then clear it — even on
        // error — so the context never leaks between steps.
        ACTIVE_DEVICE.with(|d| *d.borrow_mut() = Some(self.device.clone()));
        let out = step.run(inputs);
        ACTIVE_DEVICE.with(|d| *d.borrow_mut() = None);
        out
    }
}
