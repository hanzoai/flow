"""Schema and connectivity tests for the 3 starter agentic workflow templates."""

import json
from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
STARTER_TEMPLATES = [
    "starter_rag_workflow.json",
    "starter_router_workflow.json",
    "starter_tool_agent_workflow.json",
]


@pytest.mark.parametrize("filename", STARTER_TEMPLATES)
def test_starter_workflow_template_schema_and_edges(filename: str) -> None:
    """Verify each starter template has valid JSON, local engine endpoint, and connected edges."""
    path = TEMPLATES_DIR / filename
    assert path.exists(), f"Missing starter template: {path}"

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["name"]
    assert data["description"]
    assert data["engine_endpoint"] == "http://127.0.0.1:1234/v1"

    node_ids = {node["id"] for node in data["nodes"]}
    assert len(node_ids) >= 3
    assert len(data["edges"]) >= 2

    for edge in data["edges"]:
        assert edge["source"] in node_ids, f"Dangling source {edge['source']} in {filename}"
        assert edge["target"] in node_ids, f"Dangling target {edge['target']} in {filename}"
