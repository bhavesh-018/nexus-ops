import time
import uuid

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import Settings
from app.core.errors import ServiceUnavailableError

# Why a refresh token was revoked. Reuse of a ROTATED token signals theft; a token revoked by
# LOGOUT being presented again is just a stale client and must not end other sessions.
REASON_ROTATED = "rotated"
REASON_LOGOUT = "logout"


class TokenStore:
    """Tracks revoked tokens in Redis.

    JWTs are stateless, so on their own they can't be cancelled before they expire. Two kinds
    of Redis entries fix that. Both expire by themselves once the tokens they cover would
    have expired anyway, so the store never grows forever.

    - auth:revoked_jti:<jti>        one specific token is dead (used or logged out)
    - auth:revoke_before:<user_id>  every token issued before this moment is dead
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def revoke_token(self, jti: str, ttl_seconds: int, reason: str) -> str | None:
        """Mark a token revoked. Returns None if this call revoked it, otherwise the reason
        it had already been revoked for ("rotated" or "logout").

        SET NX is atomic, so of two simultaneous refreshes with the same token only one wins.
        """
        key = f"auth:revoked_jti:{jti}"
        try:
            created = await self._redis.set(key, reason, ex=max(ttl_seconds, 1), nx=True)
            if created:
                return None
            previous = await self._redis.get(key)
        except RedisError as exc:
            raise ServiceUnavailableError("session service unavailable") from exc
        # The key can expire between the two calls; treat that as the stricter case.
        return previous.decode() if previous else REASON_ROTATED

    async def revoke_all_for_user(self, user_id: uuid.UUID, settings: Settings) -> float:
        """Invalidate every token (access and refresh) issued to this user up to now."""
        cutoff = time.time()
        try:
            await self._redis.set(
                f"auth:revoke_before:{user_id}",
                repr(cutoff),
                ex=settings.refresh_token_days * 86_400,  # older tokens are expired by then
            )
        except RedisError as exc:
            raise ServiceUnavailableError("session service unavailable") from exc
        return cutoff

    async def revoked_before(self, user_id: uuid.UUID) -> float | None:
        try:
            value = await self._redis.get(f"auth:revoke_before:{user_id}")
        except RedisError as exc:
            raise ServiceUnavailableError("session service unavailable") from exc
        return float(value) if value is not None else None
