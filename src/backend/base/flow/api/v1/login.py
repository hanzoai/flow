from __future__ import annotations

import hmac
import json
import secrets
from typing import Annotated
from urllib.parse import quote, urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from flow.api.utils import DbSession
from flow.api.v1.schemas import Token
from flow.initial_setup.setup import get_or_create_default_folder
from flow.services.auth.iam import iam_config, iam_enabled, pkce_pair, try_validate
from flow.services.database.models.user.crud import get_user_by_id
from flow.services.database.models.user.model import UserRead
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
                headers={"Accept": "application/json"},
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
async def login_to_get_access_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
):
    auth_settings = get_settings_service().auth_settings
    try:
        auth = get_auth_service()
        user = await auth.authenticate_user(form_data.username, form_data.password, db)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        from loguru import logger

        logger.error(f"Authentication error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during authentication",
        ) from exc

    if user:
        tokens = await auth.create_user_tokens(user_id=user.id, db=db, update_last_login=True)
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
        response.set_cookie(
            "apikey_tkn_lflw",
            str(user.store_api_key),
            httponly=auth_settings.ACCESS_HTTPONLY,
            samesite=auth_settings.ACCESS_SAME_SITE,
            secure=auth_settings.ACCESS_SECURE,
            expires=None,
            domain=auth_settings.COOKIE_DOMAIN,
        )
        await get_variable_service().initialize_user_variables(user.id, db)
        from flow.api.utils.mcp.agentic_mcp import initialize_agentic_user_variables

        _ = await get_or_create_default_folder(db, user.id)

        if get_settings_service().settings.agentic_experience:
            await initialize_agentic_user_variables(user.id, db)

        return tokens
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.get("/auto_login", include_in_schema=False)
async def auto_login(response: Response, db: DbSession):
    auth_settings = get_settings_service().auth_settings

    if auth_settings.AUTO_LOGIN:
        auth = get_auth_service()
        user_id, tokens = await auth.create_user_longterm_token(db)
        response.set_cookie(
            "access_token_lf",
            tokens["access_token"],
            httponly=auth_settings.ACCESS_HTTPONLY,
            samesite=auth_settings.ACCESS_SAME_SITE,
            secure=auth_settings.ACCESS_SECURE,
            expires=None,
            domain=auth_settings.COOKIE_DOMAIN,
        )

        user = await get_user_by_id(db, user_id)

        if user:
            if user.store_api_key is None:
                user.store_api_key = ""

            response.set_cookie(
                "apikey_tkn_lflw",
                str(user.store_api_key),
                httponly=auth_settings.ACCESS_HTTPONLY,
                samesite=auth_settings.ACCESS_SAME_SITE,
                secure=auth_settings.ACCESS_SECURE,
                expires=None,
                domain=auth_settings.COOKIE_DOMAIN,
            )

            if get_settings_service().settings.agentic_experience:
                from flow.api.utils.mcp.agentic_mcp import initialize_agentic_user_variables

                await initialize_agentic_user_variables(user.id, db)

        return tokens

    return {
        "auto_login": False,
        "iam_enabled": iam_enabled(),
        "iam_login_url": "/v1/iam/login" if iam_enabled() else None,
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
                        headers={"Accept": "application/json"},
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


@router.post("/logout", include_in_schema=False)
async def logout(response: Response):
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
    return {"message": "Logout successful"}
