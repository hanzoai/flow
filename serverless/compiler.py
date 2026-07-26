"""Compile a Flow export (node/edge JSON) into a deployable Fission function.

Model A (implemented): the whole flow becomes ONE function on a Python env that
has hanzo-flow installed. The package is `runner.py` + the embedded `flow.json`;
the function calls `flow.helpers.flow.run_flow` per request.

Model B (sketched, `compile_flow_to_dag`): each model/heavy node becomes its own
function and a coordinator walks the DAG — use only for GPU isolation / per-node
scale (see FUNCTIONS.md).

This module emits a `FunctionSpec` + a build dir + the `fission` CLI commands. It
does NOT call k8s — the `/v1/functions` management API (functions/INTEGRATION.md
§3) or the CLI deploys it. No image builds here (envs are published by CI).
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

# Node types that imply model inference. A flow with any of these is a candidate
# for a GPU env (Model A) or for splitting that node out (Model B). Kept as a
# simple prefix/keyword set — the flow component registry is the source of truth;
# this is the heuristic the compiler uses without importing the whole registry.
_MODEL_NODE_KEYWORDS = ("llm", "model", "embedding", "openai", "anthropic", "zen", "huggingface")

# Default runtime env names (registered on the Fission control plane).
ENV_CPU = "flow-python"   # ghcr.io/hanzoai/flow-env      (python-env + hanzo-flow)
ENV_GPU = "flow-gpu"      # ghcr.io/hanzoai/flow-env-gpu   (same, GPU resources)


@dataclass
class FunctionSpec:
    """A compiled, deployable Fission function for one flow."""

    name: str
    env: str
    build_dir: Path
    entrypoint: str = "runner.handler"
    network: str = "mainnet"          # mainnet -> ns fission ; testnet/devnet -> ns fission-sandbox
    gpu: bool = False
    files: list[str] = field(default_factory=list)

    @property
    def namespace(self) -> str:
        return "fission" if self.network == "mainnet" else "fission-sandbox"

    def cli_commands(self) -> list[str]:
        """The `fission` CLI commands to deploy this function."""
        ns = self.namespace
        return [
            f"fission fn create --name {self.name} --env {self.env} "
            f"--src {self.build_dir}/'*' --entrypoint {self.entrypoint} -n {ns}",
            f"fission httptrigger create --name {self.name} --method POST "
            f"--url /{self.name} --function {self.name} -n {ns}",
        ]


def _flow_has_model_node(flow_json: dict) -> bool:
    nodes = flow_json.get("data", flow_json).get("nodes", [])
    for n in nodes:
        nid = json.dumps(n.get("data", {}).get("type", n.get("id", ""))).lower()
        if any(k in nid for k in _MODEL_NODE_KEYWORDS):
            return True
    return False


def compile_flow(
    flow_json: dict,
    name: str,
    *,
    runtime: str | None = None,
    network: str = "mainnet",
    gpu: bool | None = None,
    out_dir: str | Path = "build",
) -> FunctionSpec:
    """Compile `flow_json` (a Flow export) into a Model-A Fission function.

    `gpu` defaults to auto: True if the flow contains a model node and you want
    in-pod inference. The common case keeps `gpu=False` and lets model nodes call
    the LLM gateway (api.hanzo.ai/v1) — see FUNCTIONS.md "GPU placement".
    """
    if gpu is None:
        gpu = False  # default: model nodes call the gateway, flow stays CPU.
    env = runtime or (ENV_GPU if gpu else ENV_CPU)

    build_dir = Path(out_dir) / name
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    # Package = the runner + the embedded flow graph.
    (build_dir / "flow.json").write_text(json.dumps(flow_json))
    shutil.copy(Path(__file__).with_name("runner.py"), build_dir / "runner.py")

    return FunctionSpec(
        name=name,
        env=env,
        build_dir=build_dir,
        network=network,
        gpu=gpu,
        files=["runner.py", "flow.json"],
    )


def compile_flow_to_dag(flow_json: dict, name: str, *, network: str = "mainnet") -> list[FunctionSpec]:
    """Model B sketch: one function per model/heavy node + a coordinator.

    Splits out nodes that warrant isolation (GPU / independent scale); everything
    else stays in a single CPU function. The coordinator topo-walks the graph and
    invokes node functions through the router. Full impl is a follow-up — this
    returns the intended unit boundaries so the UI/caller can preview the split.
    """
    nodes = flow_json.get("data", flow_json).get("nodes", [])
    specs: list[FunctionSpec] = []
    for n in nodes:
        ntype = str(n.get("data", {}).get("type", n.get("id", ""))).lower()
        if any(k in ntype for k in _MODEL_NODE_KEYWORDS):
            # one isolated (GPU-capable) function per model node
            specs.append(
                FunctionSpec(
                    name=f"{name}-{n.get('id', ntype)}",
                    env=ENV_GPU,
                    build_dir=Path("build") / f"{name}-{n.get('id', ntype)}",
                    network=network,
                    gpu=True,
                )
            )
    # plus the coordinator (CPU) — the remaining graph + the call DAG.
    specs.append(
        FunctionSpec(name=f"{name}-coordinator", env=ENV_CPU, build_dir=Path("build") / f"{name}-coordinator", network=network)
    )
    return specs


if __name__ == "__main__":  # pragma: no cover - dev convenience
    import argparse

    ap = argparse.ArgumentParser(description="Compile a Flow export to a Fission function.")
    ap.add_argument("flow_json", help="path to the flow export JSON")
    ap.add_argument("--name", help="function name (default: flow file stem)")
    ap.add_argument("--runtime", default=None, help=f"env name (default: {ENV_CPU} / {ENV_GPU})")
    ap.add_argument("--network", default="mainnet", choices=["mainnet", "testnet", "devnet"])
    ap.add_argument("--gpu", action="store_true", help="use the GPU env (in-pod inference)")
    args = ap.parse_args()

    data = json.loads(Path(args.flow_json).read_text())
    spec = compile_flow(
        data,
        name=args.name or Path(args.flow_json).stem,
        runtime=args.runtime,
        network=args.network,
        gpu=args.gpu,
    )
    print(f"compiled '{spec.name}' -> env={spec.env} ns={spec.namespace} dir={spec.build_dir}")
    print("\n".join(spec.cli_commands()))
