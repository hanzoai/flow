"""Flow -> Hanzo Functions (Fission) compiler.

Compile a Flow graph export into a deployable Fission function. See FUNCTIONS.md
for the two models (flow-as-function, node-as-function) and GPU placement.
"""

from .compiler import FunctionSpec, compile_flow

__all__ = ["FunctionSpec", "compile_flow"]
