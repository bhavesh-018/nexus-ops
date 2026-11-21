import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.api import health
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import create_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.engine = create_engine(settings)
    app.state.redis = Redis.from_url(settings.redis_url)
    logger.info("nexusops api started (env=%s)", settings.app_env)
    yield
    await app.state.redis.aclose()
    await app.state.engine.dispose()
    logger.info("nexusops api stopped")


def create_app() -> FastAPI:
    app = FastAPI(title="NexusOps API", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    return app


app = create_app()
