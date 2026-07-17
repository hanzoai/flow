//! Proves the real hanzo-ml binding end-to-end on CPU: real `hanzo_ml::Tensor`s flow
//! through flow-core's `GpuResidentBackend` as values, a real on-device op (`affine`)
//! executes, and the numeric result is correct. No GPU, no CUDA build — the identical
//! graph runs on a CUDA/Metal device by constructing `MlDevice::cuda(0)` instead.

use std::collections::HashMap;
use std::sync::Arc;

use flow_core::gpu::{current_device, GpuResidentBackend};
use flow_core::*;
use flow_ml::{MlDevice, MlTensor};
use hanzo_ml::{DType, Device as MlDev, Tensor};

fn tensor_of(v: &ValueRef) -> Tensor {
    v.as_any().downcast_ref::<MlTensor>().expect("MlTensor").0.clone()
}

/// Recover the real hanzo_ml::Device the step is running on — what a GPU step does to
/// build/execute tensors on the injected device.
fn ml_device() -> MlDev {
    let d = current_device().expect("device injected in GpuResident mode");
    d.as_any().downcast_ref::<MlDevice>().expect("MlDevice").device().clone()
}

// Source: allocates a [2,3] ones tensor on the injected device (host→device once).
struct Ones {
    id: String,
}
impl Step for Ones {
    fn id(&self) -> &str {
        &self.id
    }
    fn ins(&self) -> Vec<Port> {
        vec![]
    }
    fn outs(&self) -> Vec<Port> {
        vec![Port::new("t", "tensor")]
    }
    fn run(&self, _in: &Inputs) -> Result<Outputs, FlowError> {
        let dev = ml_device();
        let t = Tensor::ones((2, 3), DType::F32, &dev)
            .map_err(|e| FlowError::Step { id: self.id.clone(), source: e.to_string() })?;
        Ok(HashMap::from([("t".to_string(), Arc::new(MlTensor(t)) as ValueRef)]))
    }
}

// Transform: a real on-device op — affine(2, 0) doubles every element, staying resident.
struct Double {
    id: String,
}
impl Step for Double {
    fn id(&self) -> &str {
        &self.id
    }
    fn ins(&self) -> Vec<Port> {
        vec![Port::new("t", "tensor")]
    }
    fn outs(&self) -> Vec<Port> {
        vec![Port::new("t", "tensor")]
    }
    fn run(&self, inp: &Inputs) -> Result<Outputs, FlowError> {
        let t = tensor_of(inp.get("t").expect("t"));
        let out = t
            .affine(2.0, 0.0)
            .map_err(|e| FlowError::Step { id: self.id.clone(), source: e.to_string() })?;
        Ok(HashMap::from([("t".to_string(), Arc::new(MlTensor(out)) as ValueRef)]))
    }
}

#[test]
fn ml_pipeline_runs_a_real_op_on_cpu() {
    let mut g = Graph::new();
    g.add(Arc::new(Ones { id: "ones".into() })).unwrap();
    g.add(Arc::new(Double { id: "double".into() })).unwrap();
    g.wire(PortRef::new("ones", "t"), PortRef::new("double", "t")).unwrap();

    let sched = Scheduler::new().with_backend(Box::new(GpuResidentBackend::new(Arc::new(MlDevice::cpu()))));
    let out = sched.run(&g, Mode::GpuResident, &HashMap::new()).unwrap();

    let t = tensor_of(out.get("double.t").expect("leaf"));
    assert_eq!(t.dims(), &[2, 3]);
    // The real op ran: every 1.0 became 2.0.
    assert_eq!(t.to_vec2::<f32>().unwrap(), vec![vec![2.0, 2.0, 2.0], vec![2.0, 2.0, 2.0]]);
    // And it ran on the CPU device we injected (swap MlDevice::cuda(0) → runs on GPU).
    assert!(matches!(t.device().location(), hanzo_ml::DeviceLocation::Cpu));
}

#[test]
fn ml_device_names_reflect_location() {
    assert_eq!(<MlDevice as flow_core::gpu::Device>::name(&MlDevice::cpu()), "cpu");
}
