import logging
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError, PermissionDeniedError, ServiceUnavailableError
from app.core.security import TokenType, decode_token
from app.models.enums import Role, has_role
from app.models.identity import User
from app.services.rate_limit import RateLimiter
from app.services.token_store import TokenStore

logger = logging.getLogger(__name__)

# auto_error=False so a missing token goes through our own consistent 401 handler.
bearer_scheme = HTTPBearer(auto_error=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RedisDep = Annotated[Redis, Depends(get_redis)]


def get_token_store(redis: RedisDep) -> TokenStore:
    return TokenStore(redis)


def get_rate_limiter(redis: RedisDep) -> RateLimiter:
    return RateLimiter(redis)


TokenStoreDep = Annotated[TokenStore, Depends(get_token_store)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: SessionDep,
    settings: SettingsDep,
    token_store: TokenStoreDep,
) -> User:
    if credentials is None:
        raise AuthenticationError("missing bearer token")
    claims = decode_token(credentials.credentials, TokenType.ACCESS, settings)

    # "Log out everywhere" and refresh-token reuse detection record a cutoff time; access
    # tokens issued before it are dead. Access tokens only live minutes, so if Redis is down we
    # fail open here (and log) instead of making the whole API unusable.
    try:
        cutoff = await token_store.revoked_before(claims.user_id)
    except ServiceUnavailableError:
        logger.error("revocation check unavailable, skipping (fail open)")
        cutoff = None
    if cutoff is not None and claims.issued_at < cutoff:
        raise AuthenticationError("session has been revoked")

    user = await session.get(User, claims.user_id)
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
