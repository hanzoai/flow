"""Hanzo IAM authentication seam — flow trusts Hanzo IAM instead of minting identity.

This is the one place flow validates a Hanzo IAM access token (JWKS-verified) and
resolves it to a multi-tenant principal: (org, project, user). It mirrors the cloud's
principal model (principal.Org / principal.Project) so a single IAM login is the same
session across console, studio, and flow.

Enabled by env (no compat alias — forward-only):
    FLOW_IAM_ISSUER         the IAM token issuer, e.g. https://hanzo.id  (presence = enabled)
    FLOW_IAM_JWKS_URL       the JWKS endpoint (default: <issuer>/v1/iam/.well-known/jwks)
    FLOW_IAM_CLIENT_ID      the OAuth client id (default: hanzo-flow)
    FLOW_IAM_CLIENT_SECRET  optional OAuth client secret (PKCE S256 works without one)
    FLOW_IAM_REDIRECT_URI   optional fixed callback URI (default: <request origin>/callback)
    FLOW_IAM_AUTHORIZE_URL  optional authorize endpoint (default: <issuer>/v1/iam/oauth/authorize)
    FLOW_IAM_TOKEN_URL      optional token endpoint (default: <issuer>/v1/iam/oauth/token)
    FLOW_IAM_LOGOUT_URL     optional logout endpoint (default: <issuer>/v1/iam/oauth/logout)
    FLOW_IAM_AUDIENCE       optional expected audience
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from contextvars import ContextVar
from dataclasses import dataclass
from functools import lru_cache

import jwt

# Per-request tenant scope the data layer reads.
# Set after a token validates; unset for anonymous/local paths (value None = no scope).
current_org: ContextVar[str | None] = ContextVar("flow_iam_org", default=None)
current_project: ContextVar[str | None] = ContextVar("flow_iam_project", default=None)

# Asymmetric algorithms published by hanzo.id JWKS — never HS* or none.
_ALLOWED_ALGS = ["RS256", "RS512", "ES256", "ES384", "ES512"]

# Explicit User-Agent so Cloudflare WAF does not 403 Python's default urllib UA
# when fetching the IAM JWKS document.
_JWKS_HEADERS = {
    "User-Agent": "hanzo-flow/1.8 (+https://flow.hanzo.ai)",
    "Accept": "application/json",
}


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
    client_id: str = "hanzo-flow"
    client_secret: str = ""
    redirect_uri: str = ""
    authorize_url: str = ""
    token_url: str = ""
    logout_url: str = ""
    # Claim names — org falls back through `organization` and `owner`.
    org_claim: str = "org"
    org_fallback_claim: str = "owner"
    project_claim: str = "project"
    subject_claim: str = "sub"
    username_claim: str = "name"
    email_claim: str = "email"

    def resolved_authorize_url(self) -> str:
        return self.authorize_url or f"{self.issuer}/v1/iam/oauth/authorize"

    def resolved_token_url(self) -> str:
        return self.token_url or f"{self.issuer}/v1/iam/oauth/token"

    def resolved_logout_url(self) -> str:
        return self.logout_url or f"{self.issuer}/v1/iam/oauth/logout"


def pkce_pair() -> tuple[str, str]:
    """Generate an RFC 7636 S256 (code_verifier, code_challenge) pair."""
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


@lru_cache(maxsize=1)
def iam_config() -> IAMConfig | None:
    """The IAM config from env, or None when IAM auth is not configured (issuer unset)."""
    issuer = os.getenv("FLOW_IAM_ISSUER", "").strip().rstrip("/")
    if not issuer:
        return None
    jwks_url = os.getenv("FLOW_IAM_JWKS_URL", "").strip() or f"{issuer}/v1/iam/.well-known/jwks"
    return IAMConfig(
        issuer=issuer,
        jwks_url=jwks_url,
        audience=os.getenv("FLOW_IAM_AUDIENCE", "").strip(),
        client_id=os.getenv("FLOW_IAM_CLIENT_ID", "").strip() or "hanzo-flow",
        client_secret=os.getenv("FLOW_IAM_CLIENT_SECRET", "").strip(),
        redirect_uri=os.getenv("FLOW_IAM_REDIRECT_URI", "").strip(),
        authorize_url=os.getenv("FLOW_IAM_AUTHORIZE_URL", "").strip(),
        token_url=os.getenv("FLOW_IAM_TOKEN_URL", "").strip(),
        logout_url=os.getenv("FLOW_IAM_LOGOUT_URL", "").strip(),
    )


def iam_enabled() -> bool:
    return iam_config() is not None


class HanzoIAMValidator:
    """Verifies a Hanzo IAM JWT against the IAM JWKS and extracts the tenant principal.

    The JWKS client is created from `cfg.jwks_url`; a `signing_key` may be injected to
    verify against a known key without network (used by tests). Verification pins
    asymmetric JWKS algorithms and enforces issuer (and audience when configured) —
    no alg-confusion, no unsigned.
    """

    def __init__(self, cfg: IAMConfig, signing_key: str | None = None) -> None:
        self.cfg = cfg
        self._signing_key = signing_key
        self._jwks: jwt.PyJWKClient | None = (
            None
            if signing_key
            else jwt.PyJWKClient(cfg.jwks_url, headers=_JWKS_HEADERS, cache_keys=True, lifespan=3600)
        )

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
            "algorithms": _ALLOWED_ALGS,
            "issuer": self.cfg.issuer,
            "options": options,
        }
        if self.cfg.audience:
            kwargs["audience"] = self.cfg.audience
        else:
            options["verify_aud"] = False
        claims = jwt.decode(token, self._key_for(token), **kwargs)

        owner = str(claims.get("owner") or "").strip()
        org = str(
            claims.get(self.cfg.org_claim)
            or claims.get("organization")
            or claims.get(self.cfg.org_fallback_claim)
            or ""
        ).strip()
        subject = str(claims.get(self.cfg.subject_claim) or "").strip()
        if not org or not subject:
            msg = "IAM token missing org or subject"
            raise jwt.InvalidTokenError(msg)
        username = str(
            claims.get(self.cfg.username_claim)
            or claims.get("preferred_username")
            or claims.get("displayName")
            or ""
        ).strip()
        # SuperAdmin iff IAM-validated owner == "admin" in the reserved admin org.
        # Organization-level isAdmin is never promoted to global superuser.
        is_super_admin = owner == "admin"
        return IAMPrincipal(
            user_id=subject,
            org=org,
            username=username,
            email=str(claims.get(self.cfg.email_claim) or "").strip(),
            project=str(claims.get(self.cfg.project_claim) or "").strip(),
            is_admin=is_super_admin,
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
        # Unverified ON PURPOSE and only to read `iss`, which decides WHICH validator
        # the token belongs to. Nothing is trusted from this: a token claiming our
        # issuer goes to v.validate() below, which verifies the signature and raises.
        unverified = jwt.decode(
            # nosemgrep: python.jwt.security.unverified-jwt-decode.unverified-jwt-decode
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
