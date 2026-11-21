from fastapi import APIRouter, status

from app.api.deps import ClientIp, CurrentUser, SessionDep, SettingsDep
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest, session: SessionDep, settings: SettingsDep, ip: ClientIp
) -> TokenPair:
    """Create a new organization; the registering user becomes its admin."""
    user = await auth_service.register_organization(session, body, ip)
    return auth_service.issue_tokens(user, settings)


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest, session: SessionDep, settings: SettingsDep, ip: ClientIp
) -> TokenPair:
    user = await auth_service.authenticate(session, body.email, body.password, ip)
    return auth_service.issue_tokens(user, settings)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, session: SessionDep, settings: SettingsDep) -> TokenPair:
    return await auth_service.refresh_tokens(session, body.refresh_token, settings)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
