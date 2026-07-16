"""Shared HTTP helpers and constants used by both sync and async clients."""

from __future__ import annotations

import logging
from http import HTTPStatus

import httpx

from flow_sdk.exceptions import (
    FlowAuthError,
    FlowConnectionError,
    FlowHTTPError,
    FlowNotFoundError,
    FlowValidationError,
)

_logger = logging.getLogger("flow_sdk.client")

_DEFAULT_TIMEOUT = 60.0
_HTTP_201_CREATED = HTTPStatus.CREATED.value


def _raise_for_status_code(status: int, detail: str) -> None:
    """Raise a typed SDK exception for the given HTTP status code and detail."""
    if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
        raise FlowAuthError(status, detail)
    if status == HTTPStatus.NOT_FOUND:
        raise FlowNotFoundError(status, detail)
    if status == HTTPStatus.UNPROCESSABLE_ENTITY:
        raise FlowValidationError(status, detail)
    raise FlowHTTPError(status, detail)


def _raise_for_status(response: httpx.Response) -> None:
    """Convert httpx HTTP errors into typed SDK exceptions."""
    if response.is_success:
        return
    try:
        detail = response.json().get("detail", response.text)
    except Exception:  # noqa: BLE001
        detail = response.text
    _raise_for_status_code(response.status_code, detail)


def _build_headers(api_key: str | None) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def _connection_error(base_url: str, exc: Exception) -> FlowConnectionError:
    msg = f"Could not connect to Flow at {base_url}: {exc}"
    return FlowConnectionError(msg)
