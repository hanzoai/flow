from __future__ import annotations

import asyncio
import hmac
import json
import secrets
from typing import Annotated, Any
from urllib.parse import quote, urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlmodel import select

from flow.api.utils import CurrentActiveUser, DbSession
from flow.api.v1.schemas import Token
from flow.initial_setup.setup import get_or_create_default_folder
from flow.services.auth.iam import (
    IAM_REQUEST_HEADERS,
    current_org,
    current_principal,
    get_user_iam_token,
    iam_config,
    iam_enabled,
    pkce_pair,
    try_validate,
)
from flow.services.auth.iam_org import (
    IAM_ORG_COOKIE,
    extract_org_from_request,
    is_valid_org_slug,
    resolve_active_org,
    sync_user_org,
)
from flow.services.database.models.folder.model import Folder
from flow.services.database.models.user.crud import get_user_by_id
from flow.services.database.models.user.model import User, UserRead
from flow.services.deps import get_auth_service, get_settings_service, get_variable_service
from lfx.log.logger import logger

router = APIRouter(tags=["Login"])
iam_callback_router = APIRouter(tags=["Login"])

_OIDC_TX_COOKIE = "flow_oidc_tx"
_OIDC_SCOPES = "openid profile email offline_access"


class SessionResponse(BaseModel):
    """Session validation response."""

    authenticated: bool
    user: UserRead | None = None
    store_api_key: str | None = None


def _sanitize_next(raw: str | None) -> str:
    """Allow only relative in-app paths to prevent open redirects."""
    if not raw:
        return "/"
    val = raw.strip()
    if not val.startswith("/") or val.startswith("//") or "\\" in val:
        return "/"
    return val


def _request_origin(request: Request) -> str:
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc).split(",")[0].strip()
    if host and not host.startswith(("localhost", "127.0.0.1")) and proto == "http":
        proto = "https"
    return f"{proto}://{host}"


def _resolve_redirect_uri(request: Request) -> str:
    cfg = iam_config()
    if cfg and cfg.redirect_uri:
        return cfg.redirect_uri
    return f"{_request_origin(request)}/callback"


def _is_secure_request(request: Request, redirect_uri: str) -> bool:
    return redirect_uri.startswith("https://") or (
        request.headers.get("x-forwarded-proto") or request.url.scheme
    ).startswith("https")


@router.get("/iam/config", include_in_schema=False)
async def get_iam_config():
    """Public IAM SSO discovery for the login screen."""
    cfg = iam_config()
    if cfg is None:
        return {"enabled": False}
    return {
        "enabled": True,
        "issuer": cfg.issuer,
        "client_id": cfg.client_id,
        "login_url": "/v1/iam/login",
    }


@router.get("/iam/login", include_in_schema=False)
async def iam_login(request: Request, redirect: str | None = None):
    """Begin Hanzo IAM OIDC Authorization Code + PKCE (S256) sign-in."""
    cfg = iam_config()
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hanzo IAM authentication is not configured",
        )
    state = secrets.token_urlsafe(24)
    verifier, challenge = pkce_pair()
    redirect_uri = _resolve_redirect_uri(request)
    next_path = _sanitize_next(redirect)

    params = {
        "client_id": cfg.client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": _OIDC_SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    authorize = f"{cfg.resolved_authorize_url()}?{urlencode(params)}"
    resp = RedirectResponse(url=authorize, status_code=status.HTTP_302_FOUND)
    tx_payload = json.dumps(
        {"state": state, "verifier": verifier, "redirect_uri": redirect_uri, "next": next_path},
        separators=(",", ":"),
    )
    resp.set_cookie(
        _OIDC_TX_COOKIE,
        tx_payload,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=_is_secure_request(request, redirect_uri),
        path="/",
    )
    return resp


async def _handle_iam_callback(
    request: Request,
    db: DbSession,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    """Redeem an IAM authorization code with PKCE, verify JWT, and issue session cookies."""
    cfg = iam_config()
    if cfg is None:
        return RedirectResponse(url="/login?error=iam_not_configured", status_code=status.HTTP_302_FOUND)

    if error:
        msg = error_description or error
        return RedirectResponse(url=f"/login?error={quote(msg, safe='')}", status_code=status.HTTP_302_FOUND)

    raw_tx = request.cookies.get(_OIDC_TX_COOKIE)
    if not code or not state or not raw_tx:
        return RedirectResponse(url="/login?error=missing_oauth_state", status_code=status.HTTP_302_FOUND)

    try:
        tx = json.loads(raw_tx)
        expected_state = str(tx.get("state") or "")
        verifier = str(tx.get("verifier") or "")
        redirect_uri = str(tx.get("redirect_uri") or _resolve_redirect_uri(request))
        next_path = _sanitize_next(tx.get("next"))
    except (ValueError, TypeError):
        return RedirectResponse(url="/login?error=invalid_oauth_state", status_code=status.HTTP_302_FOUND)

    if not expected_state or not hmac.compare_digest(state, expected_state) or not verifier:
        return RedirectResponse(url="/login?error=state_mismatch", status_code=status.HTTP_302_FOUND)

    token_form: dict[str, str] = {
        "grant_type": "authorization_code",
        "client_id": cfg.client_id,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    }
    if cfg.client_secret:
        token_form["client_secret"] = cfg.client_secret

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            tok_resp = await client.post(
                cfg.resolved_token_url(),
                data=token_form,
                headers=IAM_REQUEST_HEADERS,
            )
    except httpx.HTTPError:
        return RedirectResponse(url="/login?error=iam_unreachable", status_code=status.HTTP_302_FOUND)

    if tok_resp.status_code != status.HTTP_200_OK:
        return RedirectResponse(url="/login?error=token_exchange_failed", status_code=status.HTTP_302_FOUND)

    try:
        tok_data = tok_resp.json()
    except ValueError:
        return RedirectResponse(url="/login?error=invalid_token_response", status_code=status.HTTP_302_FOUND)

    access_token = str(tok_data.get("access_token") or "").strip()
    refresh_tok = str(tok_data.get("refresh_token") or "").strip()
    expires_in = int(tok_data.get("expires_in") or 0)
    if not access_token:
        return RedirectResponse(url="/login?error=missing_access_token", status_code=status.HTTP_302_FOUND)

    auth = get_auth_service()
    try:
        user = await auth._authenticate_with_iam(access_token, db)
    except Exception as exc:
        logger.warning("Hanzo IAM callback token verification failed: %s: %s", type(exc).__name__, exc)
        return RedirectResponse(url="/login?error=token_verification_failed", status_code=status.HTTP_302_FOUND)

    if user is None:
        return RedirectResponse(url="/login?error=unrecognized_issuer", status_code=status.HTTP_302_FOUND)

    await get_variable_service().initialize_user_variables(user.id, db)
    _ = await get_or_create_default_folder(db, user.id)
    if get_settings_service().settings.agentic_experience:
        from flow.api.utils.mcp.agentic_mcp import initialize_agentic_user_variables

        await initialize_agentic_user_variables(user.id, db)

    auth_settings = get_settings_service().auth_settings
    secure = _is_secure_request(request, redirect_uri) or auth_settings.ACCESS_SECURE
    access_max_age = expires_in if expires_in > 0 else auth_settings.ACCESS_TOKEN_EXPIRE_SECONDS

    resp = RedirectResponse(url=next_path, status_code=status.HTTP_302_FOUND)
    resp.delete_cookie(_OIDC_TX_COOKIE, path="/")
    resp.set_cookie(
        "access_token_lf",
        access_token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=access_max_age,
        domain=auth_settings.COOKIE_DOMAIN,
        path="/",
    )
    if refresh_tok:
        resp.set_cookie(
            "refresh_token_lf",
            refresh_tok,
            httponly=True,
            samesite="lax",
            secure=secure,
            max_age=auth_settings.REFRESH_TOKEN_EXPIRE_SECONDS,
            domain=auth_settings.COOKIE_DOMAIN,
            path="/",
        )
    if user.store_api_key:
        resp.set_cookie(
            "apikey_tkn_lflw",
            str(user.store_api_key),
            httponly=True,
            samesite="lax",
            secure=secure,
            expires=None,
            domain=auth_settings.COOKIE_DOMAIN,
            path="/",
        )
    return resp


@router.get("/iam/callback", include_in_schema=False)
async def iam_v1_callback(
    request: Request,
    db: DbSession,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    return await _handle_iam_callback(request, db, code=code, state=state, error=error, error_description=error_description)


@iam_callback_router.get("/callback", include_in_schema=False)
async def iam_root_callback(
    request: Request,
    db: DbSession,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    return await _handle_iam_callback(request, db, code=code, state=state, error=error, error_description=error_description)


@router.post("/login", response_model=Token, include_in_schema=False)
async def login_to_get_access_token():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Local password login has been removed. Sign in with Hanzo IAM at /v1/iam/login.",
    )


@router.get("/auto_login", include_in_schema=False)
async def auto_login():
    return {
        "auto_login": False,
        "iam_enabled": True,
        "iam_login_url": "/v1/iam/login",
    }


@router.post("/refresh", include_in_schema=False)
async def refresh_token(
    request: Request,
    response: Response,
    db: DbSession,
):
    auth_settings = get_settings_service().auth_settings
    token = request.cookies.get("refresh_token_lf")
    access_cookie = request.cookies.get("access_token_lf")

    # When Hanzo IAM is active, refresh via IAM's OAuth token endpoint (or keep an
    # already-valid IAM session cookie alive instead of failing local HS256 decode).
    cfg = iam_config()
    if cfg is not None:
        if token:
            form: dict[str, str] = {
                "grant_type": "refresh_token",
                "client_id": cfg.client_id,
                "refresh_token": token,
            }
            if cfg.client_secret:
                form["client_secret"] = cfg.client_secret
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    r = await client.post(
                        cfg.resolved_token_url(),
                        data=form,
                        headers=IAM_REQUEST_HEADERS,
                    )
                if r.status_code == status.HTTP_200_OK:
                    data = r.json()
                    new_access = str(data.get("access_token") or "").strip()
                    new_refresh = str(data.get("refresh_token") or token).strip()
                    expires_in = int(data.get("expires_in") or 0)
                    if new_access and try_validate(new_access) is not None:
                        secure = _is_secure_request(request, "") or auth_settings.ACCESS_SECURE
                        response.set_cookie(
                            "access_token_lf",
                            new_access,
                            httponly=True,
                            samesite="lax",
                            secure=secure,
                            max_age=expires_in if expires_in > 0 else auth_settings.ACCESS_TOKEN_EXPIRE_SECONDS,
                            domain=auth_settings.COOKIE_DOMAIN,
                            path="/",
                        )
                        if new_refresh:
                            response.set_cookie(
                                "refresh_token_lf",
                                new_refresh,
                                httponly=True,
                                samesite="lax",
                                secure=secure,
                                max_age=auth_settings.REFRESH_TOKEN_EXPIRE_SECONDS,
                                domain=auth_settings.COOKIE_DOMAIN,
                                path="/",
                            )
                        return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}
            except Exception:
                pass
        if access_cookie:
            try:
                if try_validate(access_cookie) is not None:
                    return {"access_token": access_cookie, "token_type": "bearer"}
            except Exception:
                pass

    if token:
        auth = get_auth_service()
        tokens = await auth.create_refresh_token(token, db)
        response.set_cookie(
            "refresh_token_lf",
            tokens["refresh_token"],
            httponly=auth_settings.REFRESH_HTTPONLY,
            samesite=auth_settings.REFRESH_SAME_SITE,
            secure=auth_settings.REFRESH_SECURE,
            expires=auth_settings.REFRESH_TOKEN_EXPIRE_SECONDS,
            domain=auth_settings.COOKIE_DOMAIN,
        )
        response.set_cookie(
            "access_token_lf",
            tokens["access_token"],
            httponly=auth_settings.ACCESS_HTTPONLY,
            samesite=auth_settings.ACCESS_SAME_SITE,
            secure=auth_settings.ACCESS_SECURE,
            expires=auth_settings.ACCESS_TOKEN_EXPIRE_SECONDS,
            domain=auth_settings.COOKIE_DOMAIN,
        )
        return tokens
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.get("/session", include_in_schema=False)
async def get_session(
    request: Request,
    db: DbSession,
) -> SessionResponse:
    """Validate session and return user information."""
    from flow.services.auth.utils import oauth2_login

    try:
        token = await oauth2_login(request)
        if not token:
            return SessionResponse(authenticated=False)

        user = await get_auth_service().get_current_user_from_access_token(token, db)
        if not user or not user.is_active:
            return SessionResponse(authenticated=False)

        return SessionResponse(
            authenticated=True,
            user=UserRead.model_validate(user, from_attributes=True),
        )
    except (HTTPException, ValueError) as _:
        return SessionResponse(authenticated=False)


class IamOrgSummary(BaseModel):
    name: str
    display_name: str
    role: str = "member"
    is_personal: bool = False
    is_member: bool = True
    logo: str = ""
    favicon: str = ""
    website_url: str = ""
    plan: str = ""


class IamUserProfile(BaseModel):
    id: str
    sub: str = ""
    did: str = ""
    username: str
    display_name: str
    email: str = ""
    picture: str = ""
    owner: str = ""
    is_super_admin: bool = False


class IamContextResponse(BaseModel):
    iam_enabled: bool = True
    issuer: str = "https://hanzo.ai"
    user: IamUserProfile
    active_org: str
    active_org_info: IamOrgSummary | None = None
    orgs: list[IamOrgSummary] = Field(default_factory=list)
    links: dict[str, str] = Field(default_factory=dict)


class SwitchOrgRequest(BaseModel):
    org: str


class CreateOrgRequest(BaseModel):
    name: str


def _default_iam_links(issuer: str) -> dict[str, str]:
    base = (issuer or "https://hanzo.ai").rstrip("/")
    return {
        "account": f"{base}/account",
        "billing": f"{base}/account/billing",
        "organizations": f"{base}/account/organizations",
        "app": "https://hanzo.app/flow",
        "docs": "https://docs.hanzo.ai",
    }


def _clean_avatar(raw: str | None) -> str:
    url = (raw or "").strip()
    if not url:
        return ""
    if "gravatar.com/avatar/" in url and "d=identicon" in url:
        return ""
    return url


def _format_plan_name(tier_payload: dict[str, Any] | None) -> str:
    if not isinstance(tier_payload, dict):
        return ""
    for candidate in (
        tier_payload.get("planName"),
        (tier_payload.get("tier") or {}).get("displayName") if isinstance(tier_payload.get("tier"), dict) else None,
        tier_payload.get("plan"),
        (tier_payload.get("tier") or {}).get("name") if isinstance(tier_payload.get("tier"), dict) else None,
    ):
        val = str(candidate or "").strip()
        if val:
            return val if any(c.isupper() for c in val) else val.capitalize()
    return ""


async def _fetch_json(client: httpx.AsyncClient, url: str, headers: dict[str, str]) -> dict[str, Any] | None:
    try:
        resp = await client.get(url, headers=headers)
        if resp.status_code == status.HTTP_200_OK:
            data = resp.json()
            if isinstance(data, dict):
                return data
    except Exception:
        logger.debug("IAM upstream fetch failed for %s", url, exc_info=True)
    return None


async def _ensure_org_workspace_folder(
    db: DbSession,
    user: User,
    org_slug: str,
    display_name: str,
) -> None:
    """Create a default workspace folder scoped to `org_slug` if the user has none yet."""
    existing = (
        await db.exec(
            select(Folder).where(Folder.user_id == user.id, Folder.org_id == org_slug)
        )
    ).first()
    if existing is not None:
        return

    base_name = (display_name or org_slug).strip() or org_slug
    candidate = base_name
    if (
        await db.exec(
            select(Folder).where(Folder.user_id == user.id, Folder.name == candidate)
        )
    ).first() is not None:
        candidate = f"{base_name} ({org_slug})"
        suffix = 2
        while (
            await db.exec(
                select(Folder).where(Folder.user_id == user.id, Folder.name == candidate)
            )
        ).first() is not None:
            candidate = f"{base_name} ({suffix})"
            suffix += 1

    folder = Folder(
        name=candidate,
        description=f"Workspace projects for {display_name or org_slug}",
        user_id=user.id,
        org_id=org_slug,
    )
    db.add(folder)
    await db.flush()
    await db.refresh(folder)


async def _build_iam_context(
    request: Request,
    current_user: User,
    db: DbSession,
    *,
    override_org: str | None = None,
) -> IamContextResponse:
    cfg = iam_config()
    principal = current_principal.get()
    issuer = cfg.issuer if cfg else "https://hanzo.ai"

    from flow.services.auth.utils import oauth2_login

    token = await oauth2_login(request) or get_user_iam_token(str(current_user.id)) or ""

    userinfo: dict[str, Any] = {}
    org_rows: list[dict[str, Any]] = []
    tier_payload: dict[str, Any] | None = None

    requested_org = override_org or extract_org_from_request(request)
    provisional_org = resolve_active_org(current_user, principal=principal, requested_org=requested_org) or "admin"

    if cfg is not None and token:
        base_headers = {**IAM_REQUEST_HEADERS, "Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=8.0) as client:
            ui_data, orgs_data, tier_data = await asyncio.gather(
                _fetch_json(client, cfg.resolved_userinfo_url(), base_headers),
                _fetch_json(client, cfg.resolved_orgs_url(), base_headers),
                _fetch_json(
                    client,
                    cfg.resolved_billing_tier_url(),
                    {**base_headers, "X-Org-Id": provisional_org},
                ),
            )
        if ui_data:
            userinfo = ui_data
        if orgs_data and isinstance(orgs_data.get("organizations"), list):
            org_rows = [row for row in orgs_data["organizations"] if isinstance(row, dict)]
        tier_payload = tier_data

    owner = str(userinfo.get("owner") or (principal.owner if principal else "") or "").strip()
    is_super_admin = bool(
        (principal and principal.is_admin)
        or owner == "admin"
        or current_user.is_superuser
    )

    row_by_name: dict[str, dict[str, Any]] = {}
    for row in org_rows:
        slug = str(row.get("name") or "").strip()
        if slug:
            row_by_name[slug] = row

    member_roles: dict[str, str] = {}
    if isinstance(userinfo.get("orgs"), list):
        for entry in userinfo["orgs"]:
            if isinstance(entry, dict):
                slug = str(entry.get("org") or entry.get("name") or "").strip()
                if slug:
                    member_roles[slug] = str(entry.get("role") or "member").strip()
            elif isinstance(entry, str) and entry.strip():
                member_roles.setdefault(entry.strip(), "member")
    if isinstance(userinfo.get("groups"), list):
        for grp in userinfo["groups"]:
            if isinstance(grp, str) and grp.strip():
                member_roles.setdefault(grp.strip(), "member")
    if principal is not None:
        for slug, role in principal.orgs:
            if slug:
                member_roles.setdefault(slug, role)
        if principal.org:
            member_roles.setdefault(principal.org, "admin" if principal.is_admin else "member")
    if owner:
        member_roles.setdefault(owner, "admin" if owner == "admin" else "member")
    if not member_roles and current_user.org_id:
        member_roles[current_user.org_id] = "admin" if is_super_admin else "member"

    def _make_summary(slug: str, role: str, *, is_member: bool) -> IamOrgSummary:
        row = row_by_name.get(slug, {})
        display_name = str(row.get("displayName") or "").strip()
        if not display_name:
            display_name = "Hanzo Admin" if slug == "admin" else slug
        return IamOrgSummary(
            name=slug,
            display_name=display_name,
            role=role,
            is_personal=bool(row.get("isPersonal", False)),
            is_member=is_member,
            logo=str(row.get("logoDark") or row.get("logo") or row.get("avatar") or "").strip(),
            favicon=str(row.get("favicon") or "").strip(),
            website_url=str(row.get("websiteUrl") or "").strip(),
        )

    member_summaries = [_make_summary(slug, role, is_member=True) for slug, role in member_roles.items()]
    # Personal organization leads, then direct member organizations.
    member_summaries.sort(key=lambda o: (not o.is_personal, o.name != "admin", o.display_name.lower()))

    extra_summaries: list[IamOrgSummary] = []
    if is_super_admin:
        for slug in row_by_name:
            if slug in member_roles:
                continue
            extra_summaries.append(_make_summary(slug, "superadmin", is_member=False))
        extra_summaries.sort(key=lambda o: (o.name.startswith("wallet-"), o.display_name.lower()))

    all_orgs = [*member_summaries, *extra_summaries]
    allowed_slugs = {o.name for o in all_orgs}

    active_org = override_org or extract_org_from_request(request) or current_user.org_id or ""
    if not active_org or (allowed_slugs and active_org not in allowed_slugs and not is_super_admin):
        active_org = member_summaries[0].name if member_summaries else (principal.org if principal else "admin")

    # If the effective org differed from provisional_org, fetch the real plan for active_org.
    plan_name = _format_plan_name(tier_payload)
    if cfg is not None and token and active_org != provisional_org:
        base_headers = {**IAM_REQUEST_HEADERS, "Authorization": f"Bearer {token}", "X-Org-Id": active_org}
        async with httpx.AsyncClient(timeout=6.0) as client:
            tier_data = await _fetch_json(client, cfg.resolved_billing_tier_url(), base_headers)
        plan_name = _format_plan_name(tier_data)

    active_org_info = next((o for o in all_orgs if o.name == active_org), None)
    if active_org_info is None:
        active_org_info = _make_summary(active_org, "admin" if is_super_admin else "member", is_member=True)
        all_orgs.insert(0, active_org_info)
    if plan_name:
        active_org_info.plan = plan_name

    if current_user.org_id != active_org and is_valid_org_slug(active_org):
        await sync_user_org(current_user, active_org, db)
    current_org.set(active_org)

    email = str(userinfo.get("email") or (principal.email if principal else "") or "").strip()
    if not email and "@" in current_user.username:
        email = current_user.username
    username = str(
        userinfo.get("preferred_username")
        or userinfo.get("name")
        or (principal.username if principal else "")
        or current_user.username
    ).strip()
    display_name = str(
        userinfo.get("displayName")
        or (principal.display_name if principal else "")
        or username
        or email
    ).strip()
    picture = _clean_avatar(
        str(userinfo.get("picture") or userinfo.get("avatar") or (principal.picture if principal else "") or "")
    )
    sub = str(userinfo.get("sub") or (principal.user_id if principal else "") or str(current_user.id)).strip()
    did = str(userinfo.get("did") or "").strip()

    return IamContextResponse(
        iam_enabled=cfg is not None,
        issuer=issuer,
        user=IamUserProfile(
            id=str(current_user.id),
            sub=sub,
            did=did,
            username=username,
            display_name=display_name,
            email=email,
            picture=picture,
            owner=owner or active_org,
            is_super_admin=is_super_admin,
        ),
        active_org=active_org,
        active_org_info=active_org_info,
        orgs=all_orgs,
        links=_default_iam_links(issuer),
    )


@router.get("/iam/context", response_model=IamContextResponse, include_in_schema=False)
async def get_iam_context(
    request: Request,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> IamContextResponse:
    """Return the signed-in user's live Hanzo IAM identity, active org, plan, and accessible orgs."""
    return await _build_iam_context(request, current_user, db)


@router.post("/iam/org", response_model=IamContextResponse, include_in_schema=False)
async def switch_iam_org(
    payload: SwitchOrgRequest,
    request: Request,
    response: Response,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> IamContextResponse:
    """Switch the active Hanzo IAM organization for this Flow session."""
    target = (payload.org or "").strip()
    if not is_valid_org_slug(target):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid organization slug")

    ctx = await _build_iam_context(request, current_user, db)
    allowed = {o.name for o in ctx.orgs}
    if target not in allowed and not ctx.user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have access to organization '{target}'.",
        )

    await sync_user_org(current_user, target, db)
    current_org.set(target)

    target_info = next((o for o in ctx.orgs if o.name == target), None)
    principal = current_principal.get()
    home_org = principal.org if principal else None
    if home_org and target != home_org:
        await _ensure_org_workspace_folder(
            db,
            current_user,
            target,
            target_info.display_name if target_info else target,
        )

    auth_settings = get_settings_service().auth_settings
    secure = _is_secure_request(request, "") or auth_settings.ACCESS_SECURE
    response.set_cookie(
        IAM_ORG_COOKIE,
        target,
        httponly=False,
        samesite="lax",
        secure=secure,
        max_age=60 * 60 * 24 * 30,
        domain=auth_settings.COOKIE_DOMAIN,
        path="/",
    )
    return await _build_iam_context(request, current_user, db, override_org=target)


@router.post("/iam/orgs", include_in_schema=False)
async def create_iam_org(
    payload: CreateOrgRequest,
    request: Request,
    response: Response,
    current_user: CurrentActiveUser,
    db: DbSession,
):
    """Create a real Hanzo IAM organization via POST /v1/account/orgs and switch into it."""
    name = (payload.name or "").strip()
    if len(name) < 2 or len(name) > 80:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name must be between 2 and 80 characters.",
        )

    cfg = iam_config()
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hanzo IAM is not configured")

    from flow.services.auth.utils import oauth2_login

    token = await oauth2_login(request) or get_user_iam_token(str(current_user.id)) or ""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Hanzo IAM session token")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                cfg.resolved_create_org_url(),
                json={"name": name},
                headers={
                    **IAM_REQUEST_HEADERS,
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach Hanzo IAM to create organization.",
        ) from exc

    body: dict[str, Any] = {}
    try:
        parsed = res.json()
        if isinstance(parsed, dict):
            body = parsed
    except ValueError:
        pass

    if res.status_code >= 400:
        detail = str(body.get("detail") or body.get("error") or body.get("message") or f"Failed to create organization ({res.status_code})")
        raise HTTPException(status_code=res.status_code, detail=detail)

    org_slug = str(body.get("org") or body.get("name") or "").strip()
    if not is_valid_org_slug(org_slug):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Hanzo IAM did not return an organization handle.")

    # Silently refresh the IAM token if a refresh cookie is present so the newly created org
    # is embedded in the session JWT immediately.
    refresh_cookie = request.cookies.get("refresh_token_lf")
    auth_settings = get_settings_service().auth_settings
    secure = _is_secure_request(request, "") or auth_settings.ACCESS_SECURE
    if refresh_cookie:
        try:
            form: dict[str, str] = {
                "grant_type": "refresh_token",
                "client_id": cfg.client_id,
                "refresh_token": refresh_cookie,
            }
            if cfg.client_secret:
                form["client_secret"] = cfg.client_secret
            async with httpx.AsyncClient(timeout=10.0) as client:
                ref = await client.post(cfg.resolved_token_url(), data=form, headers=IAM_REQUEST_HEADERS)
            if ref.status_code == status.HTTP_200_OK:
                ref_data = ref.json()
                new_access = str(ref_data.get("access_token") or "").strip()
                new_refresh = str(ref_data.get("refresh_token") or refresh_cookie).strip()
                expires_in = int(ref_data.get("expires_in") or 0)
                if new_access and try_validate(new_access) is not None:
                    response.set_cookie(
                        "access_token_lf",
                        new_access,
                        httponly=True,
                        samesite="lax",
                        secure=secure,
                        max_age=expires_in if expires_in > 0 else auth_settings.ACCESS_TOKEN_EXPIRE_SECONDS,
                        domain=auth_settings.COOKIE_DOMAIN,
                        path="/",
                    )
                    if new_refresh:
                        response.set_cookie(
                            "refresh_token_lf",
                            new_refresh,
                            httponly=True,
                            samesite="lax",
                            secure=secure,
                            max_age=auth_settings.REFRESH_TOKEN_EXPIRE_SECONDS,
                            domain=auth_settings.COOKIE_DOMAIN,
                            path="/",
                        )
        except Exception:
            logger.debug("Silent token refresh after org creation failed", exc_info=True)

    await sync_user_org(current_user, org_slug, db)
    current_org.set(org_slug)
    await _ensure_org_workspace_folder(db, current_user, org_slug, name)
    response.set_cookie(
        IAM_ORG_COOKIE,
        org_slug,
        httponly=False,
        samesite="lax",
        secure=secure,
        max_age=60 * 60 * 24 * 30,
        domain=auth_settings.COOKIE_DOMAIN,
        path="/",
    )
    ctx = await _build_iam_context(request, current_user, db, override_org=org_slug)
    return {"org": org_slug, "display_name": name, "context": ctx}


def _clear_session_cookies(response: Response) -> None:
    auth_settings = get_settings_service().auth_settings
    response.delete_cookie(
        "refresh_token_lf",
        httponly=auth_settings.REFRESH_HTTPONLY,
        samesite=auth_settings.REFRESH_SAME_SITE,
        secure=auth_settings.REFRESH_SECURE,
        domain=auth_settings.COOKIE_DOMAIN,
        path="/",
    )
    response.delete_cookie(
        "access_token_lf",
        httponly=auth_settings.ACCESS_HTTPONLY,
        samesite=auth_settings.ACCESS_SAME_SITE,
        secure=auth_settings.ACCESS_SECURE,
        domain=auth_settings.COOKIE_DOMAIN,
        path="/",
    )
    response.delete_cookie(
        "apikey_tkn_lflw",
        httponly=auth_settings.ACCESS_HTTPONLY,
        samesite=auth_settings.ACCESS_SAME_SITE,
        secure=auth_settings.ACCESS_SECURE,
        domain=auth_settings.COOKIE_DOMAIN,
        path="/",
    )
    response.delete_cookie(_OIDC_TX_COOKIE, path="/")
    response.delete_cookie(IAM_ORG_COOKIE, domain=auth_settings.COOKIE_DOMAIN, path="/")


@router.get("/iam/logout", include_in_schema=False)
async def iam_logout():
    """Clear Flow session cookies and return to the sign-in screen."""
    resp = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    _clear_session_cookies(resp)
    return resp


@router.post("/logout", include_in_schema=False)
async def logout(response: Response):
    _clear_session_cookies(response)
    return {"message": "Logout successful"}
