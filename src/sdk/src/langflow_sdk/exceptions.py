"""Exceptions raised by the Flow SDK."""

from __future__ import annotations


class FlowError(Exception):
    """Base class for all Flow SDK errors."""


class FlowHTTPError(FlowError):
    """An HTTP error was returned by the Flow API."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class FlowNotFoundError(FlowHTTPError):
    """The requested resource was not found (404)."""


class FlowAuthError(FlowHTTPError):
    """Authentication failed (401/403)."""


class FlowValidationError(FlowHTTPError):
    """The request payload was rejected by the server (422)."""


class FlowConnectionError(FlowError):
    """Could not connect to the Flow instance."""


class FlowTimeoutError(FlowError):
    """A background job or polling operation exceeded its timeout.

    Adapted from ``FlowV2TimeoutError`` in flow-ai/sdk PR #1
    (Janardan Singh Kavia, IBM Corp., Apache 2.0).
    """


class EnvironmentNotFoundError(FlowError):
    """The named environment is not defined in the environments config."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(
            f"Environment {name!r} not found. Check your flow-environments.toml (or FLOW_ENV variable)."
        )


class EnvironmentConfigError(FlowError):
    """The environments config file is malformed or missing required fields."""
