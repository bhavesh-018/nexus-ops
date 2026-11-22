import hashlib
import logging
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import Settings
from app.core.errors import RateLimitedError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after: int  # seconds until the window resets


class RateLimiter:
    """Fixed-window counter in Redis: allow `limit` hits per `window_seconds` per key.

    Fixed windows are simple and cheap but allow a short burst at a window boundary. That is
    acceptable for brute-force protection, where the goal is "a handful of tries", not exact
    smoothing. If Redis is down we fail open: a Redis outage must not lock everyone out of the
    product. The cost is that limits are off until Redis is back, so we log loudly.
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def hit(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        redis_key = f"ratelimit:{key}"
        try:
            # One MULTI/EXEC transaction. SET NX creates the key with its expiry only if it
            # doesn't exist yet, so the key can never be left without a TTL (which would
            # block someone forever), and INCR then counts the hit.
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.set(redis_key, 0, ex=window_seconds, nx=True)
                pipe.incr(redis_key)
                pipe.ttl(redis_key)
                _, count, ttl = await pipe.execute()
        except RedisError:
            logger.exception("rate limiter unavailable, allowing request (fail open)")
            return RateLimitResult(allowed=True, retry_after=0)
        return RateLimitResult(allowed=count <= limit, retry_after=max(int(ttl), 1))

    async def reset(self, key: str) -> None:
        try:
            await self._redis.delete(f"ratelimit:{key}")
        except RedisError:
            logger.exception("rate limiter reset failed")


async def _enforce(limiter: RateLimiter, key: str, limit: int, window: int, what: str) -> None:
    result = await limiter.hit(key, limit, window)
    if not result.allowed:
        raise RateLimitedError(
            f"too many {what}, try again in {result.retry_after} seconds", result.retry_after
        )


def _login_key(ip: str | None, email: str) -> str:
    # Hash the email so keys stay a fixed size and Redis doesn't hold plain addresses.
    digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()[:32]
    return f"login:{ip or 'unknown'}:{digest}"


async def enforce_login_limits(
    limiter: RateLimiter, settings: Settings, ip: str | None, email: str
) -> None:
    # Per (IP + email): stops password guessing on one account without letting a stranger
    # lock the real owner out from a different IP.
    await _enforce(
        limiter,
        _login_key(ip, email),
        settings.login_max_attempts,
        settings.login_window_seconds,
        "login attempts",
    )
    # Per IP: stops one machine trying many different emails ("password spraying").
    await _enforce(
        limiter,
        f"login_ip:{ip or 'unknown'}",
        settings.login_ip_max_attempts,
        settings.login_window_seconds,
        "login attempts",
    )


async def reset_login_limit(limiter: RateLimiter, ip: str | None, email: str) -> None:
    """A successful login clears the failure count for that IP + email."""
    await limiter.reset(_login_key(ip, email))


async def enforce_register_limit(limiter: RateLimiter, settings: Settings, ip: str | None) -> None:
    await _enforce(
        limiter,
        f"register:{ip or 'unknown'}",
        settings.register_max_per_window,
        settings.register_window_seconds,
        "registrations",
    )
