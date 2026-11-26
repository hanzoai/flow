"""Hanzo IAM authentication seam — flow trusts Hanzo IAM instead of minting identity.

This is the one place flow validates a Hanzo IAM access token (JWKS-verified) and
resolves it to a multi-tenant principal: (org, project, user). It mirrors the cloud's
principal model (principal.Org / principal.Project) so a single IAM login is the same
session across console, studio, and flow.

Enabled by env (no compat alias — forward-only):
    FLOW_IAM_ISSUER         the IAM token issuer, e.g. https://hanzo.ai  (presence = enabled)
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
current_iam_token: ContextVar[str | None] = ContextVar("flow_iam_token", default=None)
current_principal: ContextVar[IAMPrincipal | None] = ContextVar("flow_iam_principal", default=None)

# In-memory cache of the most recent verified Hanzo IAM bearer token per flow user_id
# so worker threads (which may not inherit ContextVars) can authenticate Hanzo Enso
# inference calls as the signed-in user without persisting tokens to disk or SQLite.
_user_iam_tokens: dict[str, str] = {}


def _norm_user_key(user_id: object) -> str:
    return str(user_id).strip().replace("-", "").lower()


def set_user_iam_token(user_id: str, token: str) -> None:
    if user_id and token:
        _user_iam_tokens[_norm_user_key(user_id)] = token


def get_user_iam_token(user_id: str | None = None) -> str | None:
    tok = current_iam_token.get()
    if tok:
        return tok
    if user_id is not None:
        return _user_iam_tokens.get(_norm_user_key(user_id))
    return None

# Asymmetric algorithms published by hanzo.id JWKS — never HS* or none.
_ALLOWED_ALGS = ["RS256", "RS512", "ES256", "ES384", "ES512"]

# Explicit User-Agent so Cloudflare WAF does not 403 Python's default urllib/httpx UA
# when calling Hanzo IAM / Cloud APIs.
IAM_REQUEST_HEADERS = {
    "User-Agent": "hanzo-flow/1.8 (+https://flow.hanzo.ai)",
    "Accept": "application/json",
}
_JWKS_HEADERS = IAM_REQUEST_HEADERS


def _extract_claim_orgs(claims: dict, primary_org: str, owner: str) -> tuple[tuple[str, str], ...]:
    """Normalize JWT `orgs` / `groups` claims into immutable (slug, role) tuples."""
    seen: dict[str, str] = {}
    raw_orgs = claims.get("orgs")
    if isinstance(raw_orgs, list):
        for entry in raw_orgs:
            if isinstance(entry, dict):
                slug = str(entry.get("org") or entry.get("name") or "").strip()
                role = str(entry.get("role") or "member").strip()
                if slug:
                    seen[slug] = role
            elif isinstance(entry, str) and entry.strip():
                seen.setdefault(entry.strip(), "member")
    raw_groups = claims.get("groups")
    if isinstance(raw_groups, list):
        for grp in raw_groups:
            if isinstance(grp, str) and grp.strip():
                seen.setdefault(grp.strip(), "member")
    if primary_org and primary_org not in seen:
        seen[primary_org] = "admin" if claims.get("isAdmin") or owner == "admin" else "member"
    if owner and owner not in seen:
        seen[owner] = "admin" if owner == "admin" else "member"
    return tuple(seen.items())


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
    display_name: str = ""
    picture: str = ""
    owner: str = ""
    orgs: tuple[tuple[str, str], ...] = ()

    def member_org_names(self) -> list[str]:
        names: list[str] = []
        for slug, _ in self.orgs:
            if slug and slug not in names:
                names.append(slug)
        for fallback in (self.org, self.owner):
            if fallback and fallback not in names:
                names.append(fallback)
        return names

    def can_access_org(self, org_slug: str) -> bool:
        slug = (org_slug or "").strip()
        if not slug:
            return False
        if self.is_admin:
            return True
        return slug in self.member_org_names()


@dataclass(frozen=True)
class IAMConfig:
    issuer: str
    jwks_url: str
    audience: str = ""
    also_issuers: tuple[str, ...] = ()
    client_id: str = "hanzo-flow"
    client_secret: str = ""
    redirect_uri: str = ""
    authorize_url: str = ""
    token_url: str = ""
    logout_url: str = ""
    api_base_url: str = ""
    # Claim names — org falls back through `organization` and `owner`.
    org_claim: str = "org"
    org_fallback_claim: str = "owner"
    project_claim: str = "project"
    subject_claim: str = "sub"
    username_claim: str = "name"
    email_claim: str = "email"

    @property
    def accepted_issuers(self) -> tuple[str, ...]:
        seen: list[str] = []
        for iss in (self.issuer, *self.also_issuers):
            clean = iss.strip().rstrip("/")
            if clean and clean not in seen:
                seen.append(clean)
        return tuple(seen)

    def resolved_api_base(self) -> str:
        return (self.api_base_url or "https://api.hanzo.ai").rstrip("/")

    def resolved_authorize_url(self) -> str:
        return self.authorize_url or f"{self.issuer}/v1/iam/oauth/authorize"

    def resolved_token_url(self) -> str:
        return self.token_url or f"{self.issuer}/v1/iam/oauth/token"

    def resolved_logout_url(self) -> str:
        return self.logout_url or f"{self.issuer}/v1/iam/oauth/logout"

    def resolved_userinfo_url(self) -> str:
        return f"{self.resolved_api_base()}/v1/iam/oauth/userinfo"

    def resolved_orgs_url(self) -> str:
        return f"{self.resolved_api_base()}/v1/iam/organizations?limit=100"

    def resolved_create_org_url(self) -> str:
        return f"{self.resolved_api_base()}/v1/account/orgs"

    def resolved_billing_tier_url(self) -> str:
        return f"{self.resolved_api_base()}/v1/billing/tier"


# Hanzo IAM mints tokens under sibling issuers sharing the same JWKS
# (https://hanzo.id for web OIDC, https://hanzo.ai for CLI, https://iam.hanzo.ai alias).
_HANZO_SIBLING_ISSUERS = ("https://hanzo.id", "https://hanzo.ai", "https://iam.hanzo.ai")


def _sibling_issuers_for(issuer: str, extra: str = "") -> tuple[str, ...]:
    out: list[str] = []
    if issuer in _HANZO_SIBLING_ISSUERS:
        out.extend(_HANZO_SIBLING_ISSUERS)
    for raw in extra.split(","):
        clean = raw.strip().rstrip("/")
        if clean and clean not in out:
            out.append(clean)
    return tuple(i for i in out if i != issuer)


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
    also = _sibling_issuers_for(issuer, os.getenv("FLOW_IAM_ISSUERS", ""))
    return IAMConfig(
        issuer=issuer,
        jwks_url=jwks_url,
        audience=os.getenv("FLOW_IAM_AUDIENCE", "").strip(),
        also_issuers=also,
        client_id=os.getenv("FLOW_IAM_CLIENT_ID", "").strip() or "hanzo-flow",
        client_secret=os.getenv("FLOW_IAM_CLIENT_SECRET", "").strip(),
        redirect_uri=os.getenv("FLOW_IAM_REDIRECT_URI", "").strip(),
        authorize_url=os.getenv("FLOW_IAM_AUTHORIZE_URL", "").strip(),
        token_url=os.getenv("FLOW_IAM_TOKEN_URL", "").strip(),
        logout_url=os.getenv("FLOW_IAM_LOGOUT_URL", "").strip(),
        api_base_url=os.getenv("FLOW_HANZO_API_URL", "").strip().rstrip("/"),
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

    def accepts_issuer(self, iss: str) -> bool:
        clean = str(iss or "").strip().rstrip("/")
        if not clean:
            return False
        accepted = set(self.cfg.accepted_issuers)
        if self.cfg.issuer.strip().rstrip("/") in _HANZO_SIBLING_ISSUERS:
            accepted.update(_HANZO_SIBLING_ISSUERS)
        return clean in accepted

    def validate(self, token: str) -> IAMPrincipal:
        """Verify `token` and return its principal. Raises jwt.InvalidTokenError on any
        failure (bad signature, wrong issuer/audience, expired, missing org/subject)."""
        options = {"require": ["exp", "iss", self.cfg.subject_claim], "verify_iss": False}
        kwargs: dict = {
            "algorithms": _ALLOWED_ALGS,
            "options": options,
        }
        if self.cfg.audience:
            kwargs["audience"] = self.cfg.audience
        else:
            options["verify_aud"] = False
        claims = jwt.decode(token, self._key_for(token), **kwargs)
        if not self.accepts_issuer(str(claims.get("iss") or "")):
            msg = "Invalid issuer"
            raise jwt.InvalidIssuerError(msg)

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
        display_name = str(claims.get("displayName") or username or "").strip()
        picture = str(claims.get("picture") or claims.get("avatar") or "").strip()
        orgs = _extract_claim_orgs(claims, org, owner)
        return IAMPrincipal(
            user_id=subject,
            org=org,
            username=username,
            email=str(claims.get(self.cfg.email_claim) or "").strip(),
            project=str(claims.get(self.cfg.project_claim) or "").strip(),
            is_admin=is_super_admin,
            display_name=display_name,
            picture=picture,
            owner=owner,
            orgs=orgs,
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
    if not v.accepts_issuer(str(unverified.get("iss", ""))):
        return None
    principal = v.validate(token)  # raises on a bad IAM token — never falls through
    current_org.set(principal.org)
    current_project.set(principal.project or None)
    current_iam_token.set(token)
    current_principal.set(principal)
    return principal
