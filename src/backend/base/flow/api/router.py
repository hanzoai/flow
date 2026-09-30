# Router for base api
from fastapi import APIRouter
from lfx.services.settings.feature_flags import FEATURE_FLAGS

from flow.api.v1 import (
    api_key_router,
    chat_router,
    endpoints_router,
    files_router,
    flow_events_router,
    flow_version_router,
    flows_router,
    folders_router,
    knowledge_bases_router,
    login_router,
    mcp_projects_router,
    mcp_router,
    model_options_router,
    models_router,
    monitor_router,
    openai_responses_router,
    projects_router,
    starter_projects_router,
    store_router,
    traces_router,
    users_router,
    validate_router,
    variables_router,
)
from flow.api.v1.voice_mode import router as voice_mode_router
from flow.api.v2 import files_router as files_router_v2
from flow.api.v2 import mcp_router as mcp_router_v2
from flow.api.v2 import registration_router as registration_router_v2
from flow.api.v2 import workflow_router as workflow_router_v2

router_v1 = APIRouter(
    prefix="/v1",
)


def include_deployment_router(target_router: APIRouter) -> None:
    """Mount deployment routes only when the deployments feature is enabled."""
    if FEATURE_FLAGS.wxo_deployments:
        from flow.api.v1.deployments import router as deployment_router

        target_router.include_router(deployment_router)


router_v1.include_router(chat_router)
router_v1.include_router(endpoints_router)
router_v1.include_router(validate_router)
router_v1.include_router(store_router)
router_v1.include_router(flows_router)
router_v1.include_router(flow_events_router)
router_v1.include_router(flow_version_router)
router_v1.include_router(users_router)
router_v1.include_router(api_key_router)
router_v1.include_router(login_router)
router_v1.include_router(variables_router)
router_v1.include_router(files_router)
router_v1.include_router(monitor_router)
router_v1.include_router(traces_router)
router_v1.include_router(folders_router)
router_v1.include_router(projects_router)
router_v1.include_router(starter_projects_router)
router_v1.include_router(knowledge_bases_router)
router_v1.include_router(mcp_router)
router_v1.include_router(voice_mode_router)
router_v1.include_router(mcp_projects_router)
router_v1.include_router(openai_responses_router)
router_v1.include_router(models_router)
router_v1.include_router(model_options_router)
include_deployment_router(router_v1)


# Agentic flow execution - lazy import to avoid circular dependency
def _include_agentic_router():
    from flow.agentic.api.router import router as agentic_router

    router_v1.include_router(agentic_router)


_include_agentic_router()

# The upstream v2 surface lives under /v1 too: one version, one prefix. Its
# paths do not collide with v1's — v2 files are /files and /files/{file_id}
# where every v1 files route has two or more segments, and v2 MCP is
# /mcp/servers where v1 MCP is /mcp/sse, /mcp/ and /mcp/streamable.
router_v1.include_router(files_router_v2)
router_v1.include_router(mcp_router_v2)
router_v1.include_router(registration_router_v2)
router_v1.include_router(workflow_router_v2)

# The API hangs off the root at /v1: the host already names the service, so
# an /api/ prefix on top would say it twice.
router = APIRouter()
router.include_router(router_v1)
