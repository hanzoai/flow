"""Every route flow serves lives under /v1 or at a fixed root path, never /api/ or /v2/."""

from fastapi.routing import APIRoute, APIWebSocketRoute
from flow.api import health_check_router, log_router
from flow.api.router import router


def _paths():
    for r in (*router.routes, *health_check_router.routes, *log_router.routes):
        if isinstance(r, (APIRoute, APIWebSocketRoute)):
            yield r.path


def test_no_route_under_api_or_v2():
    bad = sorted(p for p in _paths() if p.startswith(("/api/", "/v2/")) or p in ("/api", "/v2"))
    assert bad == []


def test_api_surface_is_v1():
    paths = list(_paths())
    assert "/v1/version" in paths
    assert "/v1/files" in paths  # the folded upstream v2 files surface
    assert "/v1/mcp/servers" in paths
    assert "/v1/workflows" in paths
