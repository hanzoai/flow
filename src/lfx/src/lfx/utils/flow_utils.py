"""Flow environment utility functions."""

import importlib.util

from lfx.log.logger import logger


class _FlowModule:
    # Static variable
    # Tri-state:
    # - None: Flow check not performed yet
    # - True: Flow is available
    # - False: Flow is not available
    _available = None

    @classmethod
    def is_available(cls):
        return cls._available

    @classmethod
    def set_available(cls, value):
        cls._available = value


def has_flow_db_backend():
    """Check if flow's database-backed memory is actually usable right now.

    True only when the `flow` package is importable AND the registered
    DatabaseService is a real one — a NoopDatabaseService (lfx run without a
    database) must dispatch to the in-memory stubs, or flow-backed message
    updates call session.get() on a NoopSession and raise spurious
    "Message with id X not found" errors mid-stream.
    """
    if not has_flow_memory():
        return False
    try:
        from lfx.services import deps
        from lfx.services.database.service import NoopDatabaseService

        return not isinstance(deps.get_db_service(), NoopDatabaseService)
    except Exception:  # noqa: BLE001 - no service manager yet means no db backend
        return False


def has_flow_memory():
    """Check if flow.memory (with database support) and MessageTable are available."""
    # Use cached check from previous invocation (if applicable)

    is_flow_available = _FlowModule.is_available()

    if is_flow_available is not None:
        return is_flow_available

    # First check (lazy load and cache check)

    module_spec = None

    try:
        module_spec = importlib.util.find_spec("flow")
    except ImportError:
        pass
    except (TypeError, ValueError) as e:
        logger.error(f"Error encountered checking for flow.memory: {e}")

    is_flow_available = module_spec is not None
    _FlowModule.set_available(is_flow_available)

    return is_flow_available
