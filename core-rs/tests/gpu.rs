//! Proves the `GpuResident` backend seam: the device is injected into steps, tensor
//! values stay device-resident (opaque handles, no host serialization), and they flow
//! zero-copy between steps. A stub `Device` stands in for hanzo-ml — no GPU needed to
//! verify the contract.

use std::any::Any;
use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

use flow_core::gpu::{current_device, Device, DeviceTensor, GpuResidentBackend};
use flow_core::*;

/// Stands in for a hanzo-ml device: hands out monotonic tensor handles (a "device
/// pointer") so a test can assert tensors were allocated on-device and stayed resident.
struct StubGpu {
    next_handle: AtomicU64,
}
impl StubGpu {
    fn new() -> Arc<Self> {
        Arc::new(Self { next_handle: AtomicU64::new(1) })
    }
    fn alloc(&self, shape: Vec<usize>) -> DeviceTensor {
        DeviceTensor {
            device: self.name().to_string(),
            handle: self.next_handle.fetch_add(1, Ordering::SeqCst),
            shape,
            dtype: "f16".into(),
        }
    }
}
impl Device for StubGpu {
    fn name(&self) -> &str {
        "stub-gpu:0"
    }
    fn as_any(&self) -> &dyn Any {
        self
    }
}

fn tensor_of(v: &ValueRef) -> &DeviceTensor {
    v.as_any().downcast_ref::<DeviceTensor>().expect("DeviceTensor")
}

/// Recover the concrete device a GPU step is running on — exactly what a real hanzo-ml
/// step does to reach its typed kernels.
fn stub() -> Arc<dyn Device> {
    current_device().expect("device injected in GpuResident mode")
}
fn alloc_on(dev: &Arc<dyn Device>, shape: Vec<usize>) -> DeviceTensor {
    dev.as_any().downcast_ref::<StubGpu>().expect("StubGpu").alloc(shape)
}

// A GPU source: allocates a resident tensor on the injected device (hanzo-ml would run
// e.g. a load-checkpoint / encode kernel here). Reaches the device via current_device.
struct GpuSource {
    id: String,
}
impl Step for GpuSource {
    fn id(&self) -> &str {
        &self.id
    }
    fn ins(&self) -> Vec<Port> {
        vec![]
    }
    fn outs(&self) -> Vec<Port> {
        vec![Port::new("latent", "tensor")]
    }
    fn run(&self, _in: &Inputs) -> Result<Outputs, FlowError> {
        let t = alloc_on(&stub(), vec![1, 4, 64, 64]);
        Ok(HashMap::from([("latent".to_string(), Arc::new(t) as ValueRef)]))
    }
}

// A GPU transform: consumes a resident tensor and produces another WITHOUT the bytes
// ever leaving the device — it reads the input handle and allocates a new resident
// output (hanzo-ml would run a sampler/step kernel here).
struct GpuSample {
    id: String,
}
impl Step for GpuSample {
    fn id(&self) -> &str {
        &self.id
    }
    fn ins(&self) -> Vec<Port> {
        vec![Port::new("latent", "tensor")]
    }
    fn outs(&self) -> Vec<Port> {
        vec![Port::new("latent", "tensor")]
    }
    fn run(&self, inp: &Inputs) -> Result<Outputs, FlowError> {
        let input = tensor_of(inp.get("latent").expect("latent"));
        assert!(input.handle > 0, "input tensor must be device-resident");
        // A real kernel reads input.handle in VRAM and writes a new resident tensor.
        let t = alloc_on(&stub(), input.shape.clone());
        Ok(HashMap::from([("latent".to_string(), Arc::new(t) as ValueRef)]))
    }
}

#[test]
fn gpu_resident_pipeline_keeps_tensors_on_device() {
    let mut g = Graph::new();
    g.add(Arc::new(GpuSource { id: "load".into() })).unwrap();
    g.add(Arc::new(GpuSample { id: "sample".into() })).unwrap();
    g.wire(PortRef::new("load", "latent"), PortRef::new("sample", "latent")).unwrap();

    let sched = Scheduler::new().with_backend(Box::new(GpuResidentBackend::new(StubGpu::new())));
    let out = sched.run(&g, Mode::GpuResident, &HashMap::new()).unwrap();

    // The terminal value is a device-resident tensor (an opaque handle, never host bytes).
    let result = tensor_of(out.get("sample.latent").expect("leaf"));
    assert_eq!(result.device, "stub-gpu:0");
    assert_eq!(result.shape, vec![1, 4, 64, 64]);
    assert!(result.handle >= 2, "sample produced a fresh resident tensor (handle {})", result.handle);
    // The intermediate (load.latent) fed the sample edge, so it isn't a leaf.
    assert!(!out.contains_key("load.latent"));
}

#[test]
fn device_not_injected_outside_gpu_mode() {
    // Outside a GpuResident exec there is no device — proving the backend is what
    // injects it (a GPU step run under InProcess would find None and can fail cleanly).
    assert!(current_device().is_none());
}

#[test]
fn gpu_backend_reports_its_mode() {
    let b = GpuResidentBackend::new(StubGpu::new());
    assert_eq!(b.mode(), Mode::GpuResident);
    assert_eq!(b.device().name(), "stub-gpu:0");
}
