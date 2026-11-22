import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from redis.asyncio import Redis

from app.api import health
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import DomainError, RateLimitedError
from app.core.logging import configure_logging
from app.db.session import create_engine, create_session_factory

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.engine = create_engine(settings)
    app.state.session_factory = create_session_factory(app.state.engine)
    app.state.redis = Redis.from_url(settings.redis_url)
    logger.info("nexusops api started (env=%s)", settings.app_env)
    yield
    await app.state.redis.aclose()
    await app.state.engine.dispose()
    logger.info("nexusops api stopped")


async def domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Turn business-rule errors into one consistent JSON shape."""
    assert isinstance(exc, DomainError)
    headers: dict[str, str] | None = None
    if exc.status_code == 401:
        headers = {"WWW-Authenticate": "Bearer"}
    elif isinstance(exc, RateLimitedError):
        headers = {"Retry-After": str(exc.retry_after)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
        headers=headers,
    )


def _resolve_cors_origins(explicit: list[str] | None) -> list[str]:
    if explicit is not None:
        return explicit
    try:
        return get_settings().cors_origins
    except ValidationError:
        return ["http://localhost:5173"]


def create_app(cors_origins: list[str] | None = None) -> FastAPI:
    app = FastAPI(title="NexusOps API", version="0.2.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_resolve_cors_origins(cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_exception_handler(DomainError, domain_error_handler)
    app.include_router(health.router)
    app.include_router(api_router)
    return app


app = create_app()
