from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security import TokenType, decode_token
from app.models.enums import Role, has_role
from app.models.identity import User

# auto_error=False so a missing token goes through our own consistent 401 handler.
bearer_scheme = HTTPBearer(auto_error=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: SessionDep,
    settings: SettingsDep,
) -> User:
    if credentials is None:
        raise AuthenticationError("missing bearer token")
    user_id = decode_token(credentials.credentials, TokenType.ACCESS, settings)
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("invalid or expired token")
    return user


def require_role(minimum: Role) -> Callable[..., Coroutine[Any, Any, User]]:
    """Dependency factory: the caller must have at least this role."""

    async def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not has_role(user.role, minimum):
            raise PermissionDeniedError(f"requires role '{minimum.value}' or higher")
        return user

    return checker


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


CurrentUser = Annotated[User, Depends(get_current_user)]
ViewerUser = Annotated[User, Depends(require_role(Role.VIEWER))]
OperatorUser = Annotated[User, Depends(require_role(Role.OPERATOR))]
AdminUser = Annotated[User, Depends(require_role(Role.ADMIN))]
ClientIp = Annotated[str | None, Depends(client_ip)]
