//! `flow-ml` — the real `hanzo-ml` binding for flow-core's `GpuResident` seam.
//!
//! [`MlDevice`] wraps a `hanzo_ml::Device` (CPU / CUDA / Metal / Vulkan / ROCm) as a
//! [`flow_core::gpu::Device`]. [`MlTensor`] wraps a `hanzo_ml::Tensor` as a
//! [`flow_core::Value`] — and a `hanzo_ml::Tensor` is *already* an `Arc`-backed,
//! device-resident handle, so this is the [`flow_core::gpu::DeviceTensor`] abstraction
//! made concrete: cloning it between steps is a refcount bump, never a host copy.
//!
//! The payoff of the seam: the *same* step code runs on CPU or GPU — only the `Device`
//! constructor differs ([`MlDevice::cpu`] vs [`MlDevice::cuda`]). Tests run on CPU (no
//! GPU, no CUDA build); production runs the identical graph on a CUDA/Metal device.

use std::any::Any;

use flow_core::gpu::Device as FlowDevice;
use flow_core::Value;
use hanzo_ml::{Device as MlDev, Tensor};

/// A flow-core [`Device`](flow_core::gpu::Device) backed by a real `hanzo_ml::Device`.
/// GPU steps recover it via `current_device().and_then(|d| d.as_any().downcast_ref())`
/// and reach the underlying `hanzo_ml::Device` with [`MlDevice::device`] to run kernels.
pub struct MlDevice {
    inner: MlDev,
    name: String,
}

impl MlDevice {
    pub fn new(inner: MlDev) -> Self {
        let name = match inner.location() {
            hanzo_ml::DeviceLocation::Cpu => "cpu".to_string(),
            hanzo_ml::DeviceLocation::Cuda { gpu_id } => format!("cuda:{gpu_id}"),
            hanzo_ml::DeviceLocation::Metal { gpu_id } => format!("metal:{gpu_id}"),
        };
        Self { inner, name }
    }
    /// The CPU device — always available, no GPU required (what tests run on).
    pub fn cpu() -> Self {
        Self::new(MlDev::Cpu)
    }
    /// A CUDA device by ordinal. Requires the `cuda` feature; the identical graph that
    /// ran on [`MlDevice::cpu`] runs here on-GPU.
    pub fn cuda(ordinal: usize) -> hanzo_ml::Result<Self> {
        Ok(Self::new(MlDev::new_cuda(ordinal)?))
    }
    /// A CUDA device if one is available, else CPU — the desktop/BYO-GPU fallback path.
    pub fn cuda_if_available(ordinal: usize) -> hanzo_ml::Result<Self> {
        Ok(Self::new(MlDev::cuda_if_available(ordinal)?))
    }
    /// The underlying `hanzo_ml::Device`, for constructing/executing tensors on it.
    pub fn device(&self) -> &MlDev {
        &self.inner
    }
}

impl FlowDevice for MlDevice {
    fn name(&self) -> &str {
        &self.name
    }
    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// A flow-core [`Value`] wrapping a device-resident `hanzo_ml::Tensor`. Its `port_type`
/// is `"tensor"` — the type GPU ports carry. Cloning is a refcount bump (the tensor is
/// `Arc`-backed), so it flows step-to-step zero-copy and never round-trips to host.
#[derive(Clone)]
pub struct MlTensor(pub Tensor);

impl MlTensor {
    pub fn into_inner(self) -> Tensor {
        self.0
    }
    pub fn tensor(&self) -> &Tensor {
        &self.0
    }
}

impl From<Tensor> for MlTensor {
    fn from(t: Tensor) -> Self {
        MlTensor(t)
    }
}

impl Value for MlTensor {
    fn port_type(&self) -> &str {
        "tensor"
    }
    fn as_any(&self) -> &dyn Any {
        self
    }
}
