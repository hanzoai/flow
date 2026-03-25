"""
Hanzo IAM Organization extraction for Flow (Langflow fork).

Extracts the IAM organization slug from:
  1. X-IAM-Org-Id request header (set by gateway)
  2. JWT `owner` claim (from Casdoor OIDC token)
  3. JWT `org` or `organization` claim (generic OIDC)

Updates the user's org_id in the database on each authenticated request.
This allows all Flow data (flows, folders, variables) to be scoped by org.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request
    from sqlmodel.ext.asyncio.session import AsyncSession

    from langflow.services.database.models.user.model import User

logger = logging.getLogger(__name__)


def extract_org_from_request(request: Request) -> str | None:
    """Extract org ID from request headers (gateway-injected).

    The Hanzo gateway injects X-IAM-Org-Id based on the authenticated
    user's IAM organization.
    """
    return (
        request.headers.get("x-iam-org-id")
        or request.headers.get("x-org-id")
        or None
    )


def extract_org_from_jwt_payload(payload: dict) -> str | None:
    """Extract org slug from a decoded JWT payload.

    Casdoor uses the `owner` field. We also check `org` and `organization`
    for compatibility with other OIDC providers.

    Skip the Casdoor built-in org as it's not a real tenant.
    """
    org = (
        payload.get("owner")
        or payload.get("org")
        or payload.get("organization")
        or None
    )
    if org and org.lower() in ("built-in", "admin"):
        return None
    return org


async def sync_user_org(
    user: User,
    org_id: str | None,
    db: AsyncSession,
) -> None:
    """Update the user's org_id if it changed.

    This is idempotent -- safe to call on every request.
    Only writes to DB if the org actually changed.
    """
    if not org_id:
        return

    if user.org_id == org_id:
        return

    user.org_id = org_id
    db.add(user)
    await db.flush()
    await db.refresh(user)
    logger.info("Updated user %s org_id to %s", user.username, org_id)
