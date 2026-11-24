"""Hanzo Enso (https://api.hanzo.ai/v1) canonical model & embedding catalog."""

from __future__ import annotations

import os

from .model_metadata import create_model_metadata

HANZO_PROVIDER_NAME = "Hanzo Enso"
DEFAULT_HANZO_BASE_URL = "https://api.hanzo.ai/v1"


def hanzo_base_url() -> str:
    """Return the configured Hanzo Enso OpenAI-compatible API base URL."""
    return (os.getenv("HANZO_AI_BASE_URL") or DEFAULT_HANZO_BASE_URL).strip().rstrip("/")


def hanzo_enso_auto_enabled() -> bool:
    """Return True when Hanzo Enso is available out of the box (IAM session or HANZO_API_KEY)."""
    return bool((os.getenv("FLOW_IAM_ISSUER") or "").strip() or (os.getenv("HANZO_API_KEY") or "").strip())


HANZO_MODELS_DETAILED = [
    create_model_metadata(
        provider=HANZO_PROVIDER_NAME,
        name="enso",
        icon="Hanzo",
        tool_calling=True,
        default=True,
    ),
    create_model_metadata(
        provider=HANZO_PROVIDER_NAME,
        name="enso-pro",
        icon="Hanzo",
        tool_calling=True,
        default=True,
    ),
    create_model_metadata(
        provider=HANZO_PROVIDER_NAME,
        name="enso-max",
        icon="Hanzo",
        tool_calling=True,
        default=True,
    ),
    create_model_metadata(
        provider=HANZO_PROVIDER_NAME,
        name="enso-flash",
        icon="Hanzo",
        tool_calling=True,
        default=True,
    ),
    create_model_metadata(
        provider=HANZO_PROVIDER_NAME,
        name="enso-ultra",
        icon="Hanzo",
        tool_calling=True,
        default=True,
    ),
    create_model_metadata(
        provider=HANZO_PROVIDER_NAME,
        name="enso-auto",
        icon="Hanzo",
        tool_calling=True,
    ),
    create_model_metadata(
        provider=HANZO_PROVIDER_NAME,
        name="enso-hybrid",
        icon="Hanzo",
        tool_calling=True,
    ),
    create_model_metadata(
        provider=HANZO_PROVIDER_NAME,
        name="hanzo/zen",
        icon="Hanzo",
        tool_calling=True,
    ),
    create_model_metadata(
        provider=HANZO_PROVIDER_NAME,
        name="anthropic/claude-sonnet-4.6",
        icon="Hanzo",
        tool_calling=True,
    ),
    create_model_metadata(
        provider=HANZO_PROVIDER_NAME,
        name="anthropic/claude-sonnet-5.5",
        icon="Hanzo",
        tool_calling=True,
    ),
    create_model_metadata(
        provider=HANZO_PROVIDER_NAME,
        name="openai/gpt-5.4",
        icon="Hanzo",
        tool_calling=True,
    ),
    create_model_metadata(
        provider=HANZO_PROVIDER_NAME,
        name="google/gemini-2.5-pro",
        icon="Hanzo",
        tool_calling=True,
    ),
]

HANZO_EMBEDDING_MODELS_DETAILED = [
    create_model_metadata(
        provider=HANZO_PROVIDER_NAME,
        name="zen-embedding",
        icon="Hanzo",
        model_type="embeddings",
        default=True,
    ),
    create_model_metadata(
        provider=HANZO_PROVIDER_NAME,
        name="zen-embedding-3",
        icon="Hanzo",
        model_type="embeddings",
        default=True,
    ),
]
