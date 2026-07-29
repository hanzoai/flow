"""Hanzo IAM authentication seam — flow trusts Hanzo IAM instead of minting identity.

This is the one place flow validates a Hanzo IAM access token (JWKS-verified) and
resolves it to a multi-tenant principal: (org, project, user). It mirrors the cloud's
principal model (principal.Org / principal.Project) so a single IAM login is the same
session across console, studio, and flow.

The module is self-contained and side-effect-free: it verifies a token and returns an
IAMPrincipal, and exposes context vars the data layer scopes queries on. Wiring lives
in services/auth/service.py; the DB user upsert + org/project query-scoping are the
follow-on phases that build on this seam.

Enabled by env (no compat alias — forward-only):
    FLOW_IAM_ISSUER    the IAM token issuer, e.g. https://iam.hanzo.ai  (presence = enabled)
    FLOW_IAM_JWKS_URL  the JWKS endpoint (default: <issuer>/.well-known/jwks)
    FLOW_IAM_AUDIENCE  optional expected audience (the flow app's IAM client id)
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from dataclasses import dataclass
from functools import lru_cache

import jwt

# Per-request tenant scope the data layer reads (phase c scopes every query on these).
# Set after a token validates; unset for anonymous/local paths (value None = no scope).
current_org: ContextVar[str | None] = ContextVar("flow_iam_org", default=None)
current_project: ContextVar[str | None] = ContextVar("flow_iam_project", default=None)


@dataclass(frozen=True)
class IAMPrincipal:
    """A validated Hanzo IAM identity. `org` is the tenant isolation root; `project` is
    the optional sub-scope; `user_id` is the stable IAM subject."""

    user_id: str
    org: str
    username: str = ""
    email: str = ""
    project: str = ""
    is_admin: bool = False


@dataclass(frozen=True)
class IAMConfig:
    issuer: str
    jwks_url: str
    audience: str = ""
    # Claim names — org falls back to the `owner` claim.
    org_claim: str = "org"
    org_fallback_claim: str = "owner"
    project_claim: str = "project"
    subject_claim: str = "sub"
    username_claim: str = "name"
    email_claim: str = "email"
    admin_claim: str = "isAdmin"


@lru_cache(maxsize=1)
def iam_config() -> IAMConfig | None:
    """The IAM config from env, or None when IAM auth is not configured (issuer unset)."""
    issuer = os.getenv("FLOW_IAM_ISSUER", "").strip().rstrip("/")
    if not issuer:
        return None
    jwks_url = os.getenv("FLOW_IAM_JWKS_URL", "").strip() or f"{issuer}/.well-known/jwks"
    return IAMConfig(issuer=issuer, jwks_url=jwks_url, audience=os.getenv("FLOW_IAM_AUDIENCE", "").strip())


def iam_enabled() -> bool:
    return iam_config() is not None


class HanzoIAMValidator:
    """Verifies a Hanzo IAM JWT against the IAM JWKS and extracts the tenant principal.

    The JWKS client is created from `cfg.jwks_url`; a `signing_key` may be injected to
    verify against a known key without network (used by tests). Verification pins RS256
    and enforces issuer (and audience when configured) — no alg-confusion, no unsigned.
    """

    def __init__(self, cfg: IAMConfig, signing_key: str | None = None) -> None:
        self.cfg = cfg
        self._signing_key = signing_key
        self._jwks: jwt.PyJWKClient | None = None if signing_key else jwt.PyJWKClient(cfg.jwks_url)

    def _key_for(self, token: str) -> str:
        if self._signing_key is not None:
            return self._signing_key
        assert self._jwks is not None
        return self._jwks.get_signing_key_from_jwt(token).key

    def validate(self, token: str) -> IAMPrincipal:
        """Verify `token` and return its principal. Raises jwt.InvalidTokenError on any
        failure (bad signature, wrong issuer/audience, expired, missing org/subject)."""
        options = {"require": ["exp", "iss", self.cfg.subject_claim]}
        kwargs: dict = {
            "algorithms": ["RS256"],
            "issuer": self.cfg.issuer,
            "options": options,
        }
        if self.cfg.audience:
            kwargs["audience"] = self.cfg.audience
        else:
            options["verify_aud"] = False
        claims = jwt.decode(token, self._key_for(token), **kwargs)

        org = str(claims.get(self.cfg.org_claim) or claims.get(self.cfg.org_fallback_claim) or "").strip()
        subject = str(claims.get(self.cfg.subject_claim) or "").strip()
        if not org or not subject:
            msg = "IAM token missing org or subject"
            raise jwt.InvalidTokenError(msg)
        return IAMPrincipal(
            user_id=subject,
            org=org,
            username=str(claims.get(self.cfg.username_claim) or "").strip(),
            email=str(claims.get(self.cfg.email_claim) or "").strip(),
            project=str(claims.get(self.cfg.project_claim) or "").strip(),
            is_admin=bool(claims.get(self.cfg.admin_claim, False)),
        )


@lru_cache(maxsize=1)
def _validator() -> HanzoIAMValidator | None:
    cfg = iam_config()
    return HanzoIAMValidator(cfg) if cfg else None


def try_validate(token: str, *, validator: HanzoIAMValidator | None = None) -> IAMPrincipal | None:
    """Validate `token` as a Hanzo IAM token and set the tenant context vars, or return
    None when IAM is disabled or the token isn't for this issuer (so the caller falls
    back to local auth). A token that IS for this issuer but fails verification raises —
    a valid-issuer token must never silently fall through to a weaker path.

    `validator` may be injected (tests); otherwise the env-configured singleton is used.
    """
    v = validator or _validator()
    if v is None or not token:
        return None
    # Peek the issuer unverified: only tokens claiming OUR issuer are IAM tokens; anything
    # else is a local token and must fall back (not error).
    try:
        unverified = jwt.decode(
            token, options={"verify_signature": False, "verify_exp": False, "verify_aud": False}
        )
    except jwt.InvalidTokenError:
        return None
    if str(unverified.get("iss", "")).rstrip("/") != v.cfg.issuer:
        return None
    principal = v.validate(token)  # raises on a bad IAM token — never falls through
    current_org.set(principal.org)
    current_project.set(principal.project or None)
    return principal
