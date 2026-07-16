"""Exceptions raised by the Hanzo Flow SDK."""

from __future__ import annotations


class LangflowError(Exception):
    """Base class for all Hanzo Flow SDK errors."""


class LangflowHTTPError(LangflowError):
    """An HTTP error was returned by the Hanzo Flow API."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class LangflowNotFoundError(LangflowHTTPError):
    """The requested resource was not found (404)."""


class LangflowAuthError(LangflowHTTPError):
    """Authentication failed (401/403)."""


class LangflowValidationError(LangflowHTTPError):
    """The request payload was rejected by the server (422)."""


class LangflowConnectionError(LangflowError):
    """Could not connect to the Hanzo Flow instance."""


class LangflowTimeoutError(LangflowError):
    """A background job or polling operation exceeded its timeout.

    Adapted from ``LangflowV2TimeoutError`` in flow-ai/sdk PR #1
    (Janardan Singh Kavia, IBM Corp., Apache 2.0).
    """


class EnvironmentNotFoundError(LangflowError):
    """The named environment is not defined in the environments config."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(
            f"Environment {name!r} not found. Check your flow-environments.toml (or LANGFLOW_ENV variable)."
        )


class EnvironmentConfigError(LangflowError):
    """The environments config file is malformed or missing required fields."""
