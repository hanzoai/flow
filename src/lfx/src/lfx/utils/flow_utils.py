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


def has_flow_db_backend() -> bool:
    """Return True iff flow-backed memory calls have a real DB to hit.

    Requires both flow to be importable AND the registered database service to be
    a non-noop implementation. Evaluated on every call because the database
    service is typically registered *after* this module is first imported (e.g.,
    from Component class definitions loaded before graph setup).
    """
    if not has_flow_memory():
        return False
    from lfx.services.database.service import NoopDatabaseService
    from lfx.services.deps import get_db_service

    try:
        return not isinstance(get_db_service(), NoopDatabaseService)
    except Exception:  # noqa: BLE001
        return False
