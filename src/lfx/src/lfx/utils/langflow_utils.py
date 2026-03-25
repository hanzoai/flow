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


def has_langflow_memory():
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
