"""Automated validation suite for Hanzo Local Engine starter agentic workflow templates."""

import json
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).parent.parent
STARTER_DIR = ROOT_DIR / "src" / "backend" / "base" / "flow" / "initial_setup" / "starter_projects"

HANZO_TEMPLATES = [
    "Hanzo Local Engine RAG.json",
    "Hanzo Agentic Router.json",
    "Hanzo Tool Agent.json",
]


@pytest.mark.parametrize("template_name", HANZO_TEMPLATES)
def test_hanzo_template_exists_and_valid(template_name: str):
    file_path = STARTER_DIR / template_name
    assert file_path.exists(), f"Starter template {template_name} must exist"

    with file_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict), f"{template_name} must be a valid JSON object"
    assert "data" in data, f"{template_name} must contain 'data' key"
    assert "nodes" in data["data"], f"{template_name} must have nodes"
    assert "edges" in data["data"], f"{template_name} must have edges"
    assert len(data["data"]["nodes"]) > 0, "Template must contain at least one node"
    assert "hanzo" in data.get("tags", []), f"{template_name} must include 'hanzo' tag"


@pytest.mark.parametrize("template_name", HANZO_TEMPLATES)
def test_hanzo_template_node_structure_and_dimensions(template_name: str):
    file_path = STARTER_DIR / template_name
    with file_path.open(encoding="utf-8") as f:
        data = json.load(f)

    for idx, node in enumerate(data["data"]["nodes"]):
        node_type = node.get("type", "unknown")
        if node_type != "noteNode":
            assert "width" not in node, f"Node {idx} of type {node_type} must not have width at root"
            assert "height" not in node, f"Node {idx} of type {node_type} must not have height at root"


@pytest.mark.parametrize("template_name", HANZO_TEMPLATES)
def test_hanzo_engine_endpoint_configuration(template_name: str):
    file_path = STARTER_DIR / template_name
    with file_path.open(encoding="utf-8") as f:
        data = json.load(f)

    found_hanzo_wire = False
    for node in data["data"]["nodes"]:
        template = node.get("data", {}).get("node", {}).get("template", {})
        if "base_url" in template and template["base_url"].get("value") == "http://127.0.0.1:1234/v1":
            found_hanzo_wire = True
            break
        model_val = template.get("model", {}).get("value")
        if isinstance(model_val, list) and model_val:
            meta = model_val[0].get("metadata", {})
            if meta.get("base_url") == "http://127.0.0.1:1234/v1":
                found_hanzo_wire = True
                break
        desc = node.get("data", {}).get("node", {}).get("description", "")
        if "127.0.0.1:1234" in str(desc):
            found_hanzo_wire = True
            break

    assert found_hanzo_wire, f"{template_name} must be wired to local hanzoai/engine at http://127.0.0.1:1234/v1"
