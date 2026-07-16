"""Self-contained tests for the Hanzo IAM auth seam — verify the crypto + claim
extraction + fall-through/reject contract without the full app (no DB, no network:
an RSA keypair is generated and the signing key injected)."""

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
    try_validate,
)

ISSUER = "https://iam.hanzo.ai"


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


def test_validate_extracts_full_principal():
    priv, pub = _keypair()
    p = _validator(pub).validate(
        _token(priv, org="acme", project="p1", name="alice", email="a@acme.co", isAdmin=True)
    )
    assert (p.org, p.project, p.user_id) == ("acme", "p1", "u-1")
    assert p.username == "alice" and p.email == "a@acme.co" and p.is_admin is True


def test_org_falls_back_to_owner_claim():
    priv, pub = _keypair()
    tok = jwt.encode(
        {"iss": ISSUER, "sub": "u2", "owner": "zoo", "exp": int(time.time()) + 300},
        priv,
        algorithm="RS256",
    )
    assert _validator(pub).validate(tok).org == "zoo"


def test_wrong_issuer_falls_through_to_local():
    # A token NOT from our IAM issuer is a local token: try_validate returns None so the
    # caller uses local auth — it must not error.
    priv, pub = _keypair()
    assert try_validate(_token(priv, iss="https://other.example"), validator=_validator(pub)) is None


def test_our_issuer_bad_signature_never_falls_through():
    # A token claiming OUR issuer but signed by a different key MUST raise, never fall back.
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
