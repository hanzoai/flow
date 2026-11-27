"""Unit tests for canonical /v1/flow/* endpoints, Bearer auth, and X-Org-Id headers."""
# pragma: allowlist secret -- fake credentials for unit testing only

from __future__ import annotations

import json
import os
import textwrap
from http import HTTPStatus
from pathlib import Path

import httpx
import pytest
import respx
from flow_sdk import (
    GRAPH_SCHEMA_VERSION,
    AsyncClient,
    Client,
    FlowNotFoundError,
    FlowStatus,
    GraphEdge,
    GraphNode,
    WorkflowGraph,
    __version__,
)
from flow_sdk.environments import get_async_client, get_client, load_environments

_API = "https://api.hanzo.ai"
_WF_ID = "8f14e45f-ceea-467a-8a3b-111111111111"
_BEARER = "hz-test-bearer-token"
_ORG = "hanzo"


@pytest.mark.unit
def test_version_matches_package() -> None:
    assert __version__ == "0.1.7"


@pytest.mark.unit
def test_default_base_url_and_headers() -> None:
    with Client(token=_BEARER, org_id=_ORG) as client:
        assert client._base_url == _API  # noqa: SLF001
        assert client._http.headers["authorization"] == f"Bearer {_BEARER}"  # noqa: SLF001
        assert client._http.headers["x-org-id"] == _ORG  # noqa: SLF001


@pytest.mark.unit
@respx.mock
def test_sync_canonical_flow_api_roundtrip() -> None:
    status_route = respx.get(f"{_API}/v1/flow/status").mock(
        return_value=httpx.Response(200, json={"reachable": True, "version": "1.8.16"})
    )
    list_route = respx.get(f"{_API}/v1/flow/workflows", params={"page": "2", "size": "10"}).mock(
        return_value=httpx.Response(200, json={"flows": [{"id": _WF_ID, "name": "triage"}], "total": 1})
    )
    create_route = respx.post(f"{_API}/v1/flow/workflows").mock(
        return_value=httpx.Response(200, json={"id": _WF_ID, "name": "triage"})
    )
    get_route = respx.get(f"{_API}/v1/flow/workflows/{_WF_ID}").mock(
        return_value=httpx.Response(200, json={"id": _WF_ID, "name": "triage", "locked": False})
    )
    patch_route = respx.patch(f"{_API}/v1/flow/workflows/{_WF_ID}").mock(
        return_value=httpx.Response(200, json={"id": _WF_ID, "name": "triage", "locked": True})
    )
    run_route = respx.post(f"{_API}/v1/flow/runs").mock(
        return_value=httpx.Response(200, json={"session_id": "sess-1", "outputs": []})
    )
    runs_route = respx.get(f"{_API}/v1/flow/runs", params={"workflow": _WF_ID}).mock(
        return_value=httpx.Response(200, json={"vertex_builds": {}})
    )
    del_route = respx.delete(f"{_API}/v1/flow/workflows/{_WF_ID}").mock(return_value=httpx.Response(200, json={}))

    graph = WorkflowGraph(
        nodes=[GraphNode(id="n1", type="input"), GraphNode(id="n2", type="llm")],
        edges=[GraphEdge(id="e1", source="n1", sourceHandle="out", target="n2", targetHandle="in")],
    )

    with Client(token=_BEARER, org_id=_ORG) as client:
        st = client.flow_status()
        assert isinstance(st, FlowStatus)
        assert st.reachable is True
        assert st.version == "1.8.16"

        listed = client.list_workflows(page=2, size=10)
        assert listed["total"] == 1

        created = client.create_workflow("triage", description="route tickets", data=graph)
        assert created["id"] == _WF_ID

        fetched = client.get_workflow(_WF_ID)
        assert fetched["locked"] is False

        patched = client.update_workflow(_WF_ID, locked=True)
        assert patched["locked"] is True

        ran = client.run_workflow(_WF_ID, input_value="hello", session="sess-1", tweaks={"n2": {"temp": 0}})
        assert ran["session_id"] == "sess-1"

        runs = client.list_runs(_WF_ID)
        assert "vertex_builds" in runs

        client.delete_workflow(_WF_ID)

    assert status_route.calls.last.request.headers["authorization"] == f"Bearer {_BEARER}"
    assert status_route.calls.last.request.headers["x-org-id"] == _ORG
    assert list_route.called
    assert get_route.called
    assert runs_route.called
    assert del_route.called

    create_body = json.loads(create_route.calls.last.request.content)
    assert create_body["name"] == "triage"
    assert create_body["data"]["schema"] == GRAPH_SCHEMA_VERSION
    assert create_body["data"]["edges"][0]["sourceHandle"] == "out"

    patch_body = json.loads(patch_route.calls.last.request.content)
    assert patch_body == {"locked": True}

    run_body = json.loads(run_route.calls.last.request.content)
    assert run_body == {"workflow": _WF_ID, "input": "hello", "session": "sess-1", "tweaks": {"n2": {"temp": 0}}}


@pytest.mark.unit
@respx.mock
async def test_async_canonical_flow_api_roundtrip() -> None:
    respx.get(f"{_API}/v1/flow/status").mock(
        return_value=httpx.Response(200, json={"reachable": True, "version": "1.8.16"})
    )
    respx.get(f"{_API}/v1/flow/workflows").mock(return_value=httpx.Response(200, json=[]))
    respx.post(f"{_API}/v1/flow/workflows").mock(return_value=httpx.Response(200, json={"id": _WF_ID, "name": "w"}))
    respx.get(f"{_API}/v1/flow/workflows/{_WF_ID}").mock(
        return_value=httpx.Response(200, json={"id": _WF_ID, "name": "w"})
    )
    respx.patch(f"{_API}/v1/flow/workflows/{_WF_ID}").mock(
        return_value=httpx.Response(200, json={"id": _WF_ID, "name": "w2"})
    )
    respx.post(f"{_API}/v1/flow/runs").mock(return_value=httpx.Response(200, json={"session_id": "s2", "outputs": []}))
    respx.get(f"{_API}/v1/flow/runs", params={"workflow": _WF_ID}).mock(return_value=httpx.Response(200, json={}))
    respx.delete(f"{_API}/v1/flow/workflows/{_WF_ID}").mock(return_value=httpx.Response(200, json={}))

    async with AsyncClient(token=_BEARER, org_id=_ORG) as client:
        assert (await client.flow_status()).reachable is True
        assert await client.list_workflows() == []
        assert (await client.create_workflow("w"))["id"] == _WF_ID
        assert (await client.get_workflow(_WF_ID))["name"] == "w"
        assert (await client.update_workflow(_WF_ID, name="w2"))["name"] == "w2"
        assert (await client.run_workflow(_WF_ID, input_value="hi"))["session_id"] == "s2"
        assert await client.list_runs(_WF_ID) == {}
        await client.delete_workflow(_WF_ID)


@pytest.mark.unit
@respx.mock
def test_rfc7807_error_decoding() -> None:
    respx.get(f"{_API}/v1/flow/workflows/{_WF_ID}").mock(
        return_value=httpx.Response(
            404,
            json={"title": "Not Found", "status": 404, "detail": "workflow not found"},
        )
    )
    with Client(token=_BEARER, org_id=_ORG) as client:
        with pytest.raises(FlowNotFoundError) as exc_info:
            client.get_workflow(_WF_ID)
        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert exc_info.value.detail == "workflow not found"


@pytest.mark.unit
def test_environment_config_supports_token_and_org_id(tmp_path: Path) -> None:
    config = tmp_path / "flow-environments.toml"
    config.write_text(
        textwrap.dedent("""\
            [environments.prod]
            url = "https://api.hanzo.ai"
            token_env = "TEST_FLOW_BEARER_TOKEN"
            org_id = "hanzo"

            [defaults]
            environment = "prod"
        """),
        encoding="utf-8",
    )
    os.environ["TEST_FLOW_BEARER_TOKEN"] = _BEARER
    try:
        envs = load_environments(config)
        assert envs["prod"].token == _BEARER
        assert envs["prod"].org_id == "hanzo"

        with get_client("prod", config_file=config) as client:
            assert client._http.headers["authorization"] == f"Bearer {_BEARER}"  # noqa: SLF001
            assert client._http.headers["x-org-id"] == "hanzo"  # noqa: SLF001

        async_client = get_async_client("prod", config_file=config)
        assert async_client._http.headers["authorization"] == f"Bearer {_BEARER}"  # noqa: SLF001
        assert async_client._http.headers["x-org-id"] == "hanzo"  # noqa: SLF001
    finally:
        os.environ.pop("TEST_FLOW_BEARER_TOKEN", None)
