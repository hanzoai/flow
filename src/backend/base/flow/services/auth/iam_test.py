"""Self-contained tests for the Hanzo IAM auth seam — verify the crypto + claim
extraction + fall-through/reject contract + PKCE + config without the full app."""

import base64
import hashlib
import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from flow.services.auth.iam import (
    HanzoIAMValidator,
    IAMConfig,
    current_org,
    current_project,
    iam_config,
    pkce_pair,
    try_validate,
)

ISSUER = "https://hanzo.id"


def _keypair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return priv, pub


def _token(priv: str, **claims) -> str:
    payload = {"iss": ISSUER, "sub": "u-1", "org": "acme", "exp": int(time.time()) + 300}
    payload.update(claims)
    return jwt.encode(payload, priv, algorithm="RS256")


def _validator(pub: str) -> HanzoIAMValidator:
    return HanzoIAMValidator(IAMConfig(issuer=ISSUER, jwks_url="unused"), signing_key=pub)


def test_validate_extracts_full_principal_and_enforces_superadmin_predicate():
    priv, pub = _keypair()
    # Org isAdmin in a non-admin org is NOT global superuser.
    p = _validator(pub).validate(
        _token(priv, org="acme", owner="acme", project="p1", name="alice", email="a@acme.co", isAdmin=True)
    )
    assert (p.org, p.project, p.user_id) == ("acme", "p1", "u-1")
    assert p.username == "alice" and p.email == "a@acme.co" and p.is_admin is False

    # Reserved admin org owner == "admin" IS global superuser.
    admin_p = _validator(pub).validate(
        _token(priv, org="admin", owner="admin", name="z", email="z@hanzo.ai")
    )
    assert admin_p.is_admin is True


def test_org_falls_back_to_organization_and_owner_claims():
    priv, pub = _keypair()
    tok_org = jwt.encode(
        {"iss": ISSUER, "sub": "u2", "organization": "hanzo", "exp": int(time.time()) + 300},
        priv,
        algorithm="RS256",
    )
    assert _validator(pub).validate(tok_org).org == "hanzo"

    tok_owner = jwt.encode(
        {"iss": ISSUER, "sub": "u3", "owner": "zoo", "exp": int(time.time()) + 300},
        priv,
        algorithm="RS256",
    )
    assert _validator(pub).validate(tok_owner).org == "zoo"


def test_wrong_issuer_falls_through_to_local():
    priv, pub = _keypair()
    assert try_validate(_token(priv, iss="https://other.example"), validator=_validator(pub)) is None


def test_our_issuer_bad_signature_never_falls_through():
    priv_wrong, _ = _keypair()
    _, pub = _keypair()
    with pytest.raises(jwt.InvalidTokenError):
        try_validate(_token(priv_wrong), validator=_validator(pub))


def test_missing_org_and_subject_rejected():
    priv, pub = _keypair()
    v = _validator(pub)
    no_org = jwt.encode({"iss": ISSUER, "sub": "u3", "exp": int(time.time()) + 300}, priv, algorithm="RS256")
    with pytest.raises(jwt.InvalidTokenError):
        v.validate(no_org)


def test_expired_token_rejected():
    priv, pub = _keypair()
    expired = _token(priv, exp=int(time.time()) - 10)
    with pytest.raises(jwt.InvalidTokenError):
        _validator(pub).validate(expired)


def test_success_sets_tenant_context_vars():
    priv, pub = _keypair()
    current_org.set(None)
    current_project.set(None)
    p = try_validate(_token(priv, org="acme", project="proj9"), validator=_validator(pub))
    assert p is not None
    assert current_org.get() == "acme"
    assert current_project.get() == "proj9"


def test_pkce_pair_is_valid_rfc7636_s256():
    verifier, challenge = pkce_pair()
    assert len(verifier) >= 43
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    assert challenge == expected


def test_iam_config_defaults_match_hanzo_id(monkeypatch):
    iam_config.cache_clear()
    monkeypatch.setenv("FLOW_IAM_ISSUER", "https://hanzo.id/")
    monkeypatch.delenv("FLOW_IAM_JWKS_URL", raising=False)
    monkeypatch.delenv("FLOW_IAM_CLIENT_ID", raising=False)
    cfg = iam_config()
    assert cfg is not None
    assert cfg.issuer == "https://hanzo.id"
    assert cfg.client_id == "hanzo-flow"
    assert cfg.jwks_url == "https://hanzo.id/v1/iam/.well-known/jwks"
    assert cfg.resolved_authorize_url() == "https://hanzo.id/v1/iam/oauth/authorize"
    assert cfg.resolved_token_url() == "https://hanzo.id/v1/iam/oauth/token"
    iam_config.cache_clear()


def test_jwks_client_sets_non_urllib_user_agent():
    v = HanzoIAMValidator(IAMConfig(issuer=ISSUER, jwks_url="https://hanzo.ai/v1/iam/.well-known/jwks"))
    assert v._jwks is not None
    ua = v._jwks.headers.get("User-Agent", "")
    assert ua.startswith("hanzo-flow/")
    assert "urllib" not in ua.lower()


def test_user_iam_token_roundtrip():
    from flow.services.auth.iam import current_iam_token, get_user_iam_token, set_user_iam_token

    current_iam_token.set(None)
    set_user_iam_token("user-42", "jwt-abc")
    assert get_user_iam_token("user-42") == "jwt-abc"
    current_iam_token.set("jwt-ctx")
    assert get_user_iam_token("user-42") == "jwt-ctx"
    current_iam_token.set(None)


def test_user_iam_token_normalizes_uuid_formats():
    from uuid import UUID

    from flow.services.auth.iam import current_iam_token, get_user_iam_token, set_user_iam_token

    raw_hex = "12aaab39c6e64fb48ce0c8e435b66439"
    uid = UUID(raw_hex)
    current_iam_token.set(None)
    set_user_iam_token(str(uid), "iam-jwt-uuid")
    assert get_user_iam_token(raw_hex) == "iam-jwt-uuid"
    assert get_user_iam_token(str(uid)) == "iam-jwt-uuid"


def test_hanzo_enso_credentials_fallback_when_api_key_is_var_name(monkeypatch):
    from uuid import UUID

    from lfx.base.models.unified_models.credentials import get_api_key_for_provider

    from flow.services.auth.iam import current_iam_token, set_user_iam_token

    monkeypatch.delenv("HANZO_API_KEY", raising=False)
    uid = UUID("12aaab39-c6e6-4fb4-8ce0-c8e435b66439")
    current_iam_token.set(None)
    set_user_iam_token(str(uid), "iam-jwt-fallback")
    assert get_api_key_for_provider(uid, "Hanzo Enso", "HANZO_API_KEY") == "iam-jwt-fallback"
