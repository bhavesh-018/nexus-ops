from fastapi import APIRouter, Response, status

from app.api.deps import (
    ClientIp,
    CurrentUser,
    RateLimiterDep,
    SessionDep,
    SettingsDep,
    TokenStoreDep,
)
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserOut
from app.services import auth as auth_service
from app.services import rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    session: SessionDep,
    settings: SettingsDep,
    limiter: RateLimiterDep,
    ip: ClientIp,
) -> TokenPair:
    """Create a new organization; the registering user becomes its admin."""
    await rate_limit.enforce_register_limit(limiter, settings, ip)
    user = await auth_service.register_organization(session, body, ip)
    return auth_service.issue_tokens(user, settings)


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    session: SessionDep,
    settings: SettingsDep,
    limiter: RateLimiterDep,
    ip: ClientIp,
) -> TokenPair:
    await rate_limit.enforce_login_limits(limiter, settings, ip, body.email)
    user = await auth_service.authenticate(session, body.email, body.password, ip)
    await rate_limit.reset_login_limit(limiter, ip, body.email)
    return auth_service.issue_tokens(user, settings)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    session: SessionDep,
    settings: SettingsDep,
    token_store: TokenStoreDep,
    ip: ClientIp,
) -> TokenPair:
    """Single-use: the old refresh token stops working as soon as it is exchanged."""
    return await auth_service.refresh_tokens(
        session, token_store, body.refresh_token, settings, ip
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    session: SessionDep,
    settings: SettingsDep,
    token_store: TokenStoreDep,
    ip: ClientIp,
) -> Response:
    """End this device's session by revoking its refresh token."""
    await auth_service.logout(session, token_store, body.refresh_token, settings, ip)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    user: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
    token_store: TokenStoreDep,
    ip: ClientIp,
) -> Response:
    """End every session of the caller, on every device (access tokens included)."""
    await auth_service.logout_all(session, token_store, user, settings, ip)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
