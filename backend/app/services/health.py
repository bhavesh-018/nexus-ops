import logging

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def check_database(engine: AsyncEngine) -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("database readiness check failed")
        return False


async def check_redis(redis: Redis) -> bool:
    try:
        return bool(await redis.ping())
    except Exception:
        logger.exception("redis readiness check failed")
        return False


async def readiness(engine: AsyncEngine, redis: Redis) -> dict[str, bool]:
    return {"database": await check_database(engine), "redis": await check_redis(redis)}
