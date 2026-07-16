"""Flow Agentic Flows.

This package contains flow definitions for the Flow Assistant feature.

Available flows:
- translation_flow: Intent classification and translation flow (Python)
- FlowAssistant.json: Main assistant flow for Q&A and component generation (JSON)
"""

from flow.agentic.flows.flow_assistant import get_graph as get_flow_assistant_graph
from flow.agentic.flows.translation_flow import get_graph as get_translation_flow_graph

__all__ = [
    "get_translation_flow_graph",
]
