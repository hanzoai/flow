"""In-function entry for a flow deployed as a Hanzo Function (Model A).

The Fission Python env imports this module and calls `handler(context)` per
request. The package ships this file plus `flow.json` (the compiled flow export).
On each request we build the graph fresh and run it — identical to how the Flow
server executes a flow (flow.helpers.flow.run_flow / Graph.from_payload), so
behaviour matches the editor.

Identity is the gateway-minted X-User-Id / X-Org-Id (see functions/INTEGRATION.md);
billing is handled by the router's usagemeter — nothing to do here.
"""

from __future__ import annotations

import json
from pathlib import Path

_FLOW_PATH = Path(__file__).with_name("flow.json")


async def _run(input_value: str, tweaks: dict | None, user_id: str):
    # Imported lazily so the module loads even outside the flow env (e.g. tests).
    from flow.graph.graph.base import Graph
    from flow.helpers.flow import run_flow

    flow_json = json.loads(_FLOW_PATH.read_text())
    payload = flow_json.get("data", flow_json)
    graph = Graph.from_payload(payload, flow_id=flow_json.get("id"), flow_name=flow_json.get("name"))

    outputs = await run_flow(
        inputs={"input_value": input_value, "type": "chat"},
        tweaks=tweaks,
        graph=graph,
        user_id=user_id,
        output_type="chat",
    )
    # RunOutputs -> JSON-able
    return [o.model_dump() if hasattr(o, "model_dump") else str(o) for o in outputs]


def handler(context):
    """Fission Python env entrypoint.

    Body: {"input_value": str, "tweaks": dict?}. Identity from gateway headers.
    """
    import asyncio

    body = context.request.get_json(silent=True) or {}
    input_value = body.get("input_value", "")
    tweaks = body.get("tweaks")
    # Gateway-minted identity (trust boundary). Fall back to a service id offline.
    user_id = context.request.headers.get("X-User-Id", "anonymous")

    try:
        result = asyncio.run(_run(input_value, tweaks, user_id))
        return {"status": 200, "body": json.dumps({"outputs": result})}
    except Exception as exc:  # surface a clean error to the caller
        return {"status": 500, "body": json.dumps({"error": str(exc)})}
