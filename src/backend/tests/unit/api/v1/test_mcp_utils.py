from types import SimpleNamespace

import pytest
from flow.api.v1 import mcp_utils


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


class FakeSession:
    def __init__(self, flows, user_files):
        self._flows = flows
        self._user_files = user_files

    async def exec(self, stmt):
        entity = stmt.column_descriptions[0].get("entity") if stmt.column_descriptions else None
        entity_name = getattr(entity, "__name__", None)
        if entity_name == "Flow":
            return FakeResult(self._flows)
        if entity_name == "File":
            return FakeResult(self._user_files)
        return FakeResult([])


class FakeSessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeStorageService:
    def __init__(self, files_by_flow, file_bytes: dict[str, bytes] | None = None):
        self._files_by_flow = files_by_flow
        self._file_bytes = file_bytes or {}

    async def list_files(self, flow_id: str):
        return self._files_by_flow.get(flow_id, [])

    async def get_file(self, flow_id: str, file_name: str) -> bytes:
        key = f"{flow_id}/{file_name}"
        if key not in self._file_bytes:
            msg = f"File {file_name} not found in flow {flow_id}"
            raise FileNotFoundError(msg)
        return self._file_bytes[key]


@pytest.mark.asyncio
async def test_handle_list_resources_includes_flow_and_user_files(monkeypatch):
    user_id = "user-123"
    flow_id = "flow-456"

    flows = [SimpleNamespace(id=flow_id, name="Flow Node")]
    user_files = [
        SimpleNamespace(
            name="summary.pdf",
            path=f"{user_id}/uploaded-summary.pdf",
            provider="File Manager",
        )
    ]

    fake_session = FakeSession(flows=flows, user_files=user_files)
    storage_service = FakeStorageService({flow_id: ["flow-doc.docx"]})

    monkeypatch.setattr(mcp_utils, "session_scope", lambda: FakeSessionContext(fake_session))
    monkeypatch.setattr(mcp_utils, "get_storage_service", lambda: storage_service)
    monkeypatch.setattr(
        mcp_utils,
        "get_settings_service",
        lambda: SimpleNamespace(settings=SimpleNamespace(host="localhost", port=4000)),
    )

    token = mcp_utils.current_user_ctx.set(SimpleNamespace(id=user_id))
    try:
        resources = await mcp_utils.handle_list_resources()
    finally:
        mcp_utils.current_user_ctx.reset(token)

    uris = {str(resource.uri) for resource in resources}
    assert f"http://localhost:4000/v1/files/download/{flow_id}/flow-doc.docx" in uris
    assert f"http://localhost:4000/v1/files/download/{user_id}/uploaded-summary.pdf" in uris
