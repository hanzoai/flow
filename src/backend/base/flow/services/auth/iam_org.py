"""Hanzo IAM Organization extraction and workspace scoping for Flow.

Extracts the active IAM organization slug from:
  1. X-IAM-Org-Id / X-Org-Id request header (frontend switcher or API gateway)
  2. hanzo_flow_org cookie (persisted across reloads / SSR / streaming requests)
  3. Persisted user.org_id in the database
  4. Verified IAM JWT `org` / `organization` / `owner` claim

Authorizes requested org switches against the verified IAM principal so non-SuperAdmin
users can only scope into organizations they actually belong to.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from sqlalchemy import or_

if TYPE_CHECKING:
    from fastapi import Request
    from sqlmodel.ext.asyncio.session import AsyncSession

    from flow.services.auth.iam import IAMPrincipal
    from flow.services.database.models.user.model import User

logger = logging.getLogger(__name__)

IAM_ORG_COOKIE = "hanzo_flow_org"
_ORG_SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")


def is_valid_org_slug(org_id: str | None) -> bool:
    if not org_id:
        return False
    return bool(_ORG_SLUG_RE.match(org_id.strip()))


def extract_org_from_request(request: Request) -> str | None:
    """Extract requested org slug from headers or cookie, validated as a safe slug."""
    raw = (
        request.headers.get("x-iam-org-id")
        or request.headers.get("x-org-id")
        or request.cookies.get(IAM_ORG_COOKIE)
        or ""
    ).strip()
    if is_valid_org_slug(raw):
        return raw
    return None


def extract_org_from_jwt_payload(payload: dict) -> str | None:
    """Extract org slug from a decoded JWT payload."""
    org = str(
        payload.get("org")
        or payload.get("organization")
        or payload.get("owner")
        or ""
    ).strip()
    if not is_valid_org_slug(org) or org.lower() == "built-in":
        return None
    return org


def resolve_active_org(
    user: User,
    principal: IAMPrincipal | None = None,
    requested_org: str | None = None,
) -> str | None:
    """Resolve the active org for this request, enforcing IAM membership."""
    if requested_org and is_valid_org_slug(requested_org):
        if principal is None or principal.can_access_org(requested_org) or user.org_id == requested_org:
            return requested_org

    if user.org_id and is_valid_org_slug(user.org_id):
        if principal is None or principal.can_access_org(user.org_id):
            return user.org_id

    if principal is not None and is_valid_org_slug(principal.org):
        return principal.org

    return user.org_id or None


def org_scope_clause(column: Any, active_org: str | None, home_org: str | None) -> Any | None:
    """Build a SQLAlchemy WHERE clause scoping rows by `org_id`.

    Rows with `org_id IS NULL` (legacy pre-multi-org projects/flows) remain visible in
    the user's home/default org so existing workspaces never disappear on upgrade, while
    switching to any other org strictly isolates that org's projects and flows.
    """
    if not active_org:
        return None
    if not home_org or active_org == home_org:
        return or_(column == active_org, column == None)  # noqa: E711
    return column == active_org


def active_org_for_user(user: User) -> tuple[str | None, str | None]:
    """Return `(active_org, home_org)` for the current request context."""
    from flow.services.auth.iam import current_org, current_principal, iam_enabled

    if not iam_enabled():
        return None, None
    principal = current_principal.get()
    home_org = principal.org if principal is not None else None
    active_org = current_org.get() or getattr(user, "org_id", None) or home_org
    return active_org, home_org


async def sync_user_org(
    user: User,
    org_id: str | None,
    db: AsyncSession,
) -> None:
    """Update the user's org_id if it changed.

    This is idempotent -- safe to call on every request.
    Only writes to DB if the org actually changed.
    """
    if not org_id or not is_valid_org_slug(org_id):
        return

    if user.org_id == org_id:
        return

    user.org_id = org_id
    db.add(user)
    await db.flush()
    await db.refresh(user)
    logger.info("Updated user %s org_id to %s", user.username, org_id)
