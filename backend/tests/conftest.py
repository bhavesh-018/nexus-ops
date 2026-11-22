import os
import random
import subprocess
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings, get_settings
from app.db.session import create_engine, create_session_factory
from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    """Bring the real database to the latest schema before integration tests run."""
    if os.getenv("RUN_INTEGRATION") != "1":
        return
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND_DIR, check=True
    )


@asynccontextmanager
async def running_app(overrides: dict[str, int] | None = None) -> AsyncIterator[FastAPI]:
    """The real app wired to real Postgres and Redis. `overrides` change settings values."""
    settings = get_settings()
    app = create_app()
    app.state.engine = create_engine(settings)
    app.state.session_factory = create_session_factory(app.state.engine)
    app.state.redis = Redis.from_url(settings.redis_url)
    if overrides:
        patched = settings.model_copy(update=overrides)
        app.dependency_overrides[get_settings] = lambda: patched
    try:
        yield app
    finally:
        await app.state.redis.aclose()
        await app.state.engine.dispose()


# Effectively no limits, so ordinary tests (which register and log in from one IP many
# times, against a Redis that keeps counters between runs) are never throttled.
RELAXED_LIMITS = {
    "login_max_attempts": 100_000,
    "login_ip_max_attempts": 100_000,
    "register_max_per_window": 100_000,
}

# Tight limits for the rate-limit tests.
STRICT_LIMITS = {
    "login_max_attempts": 3,
    "login_ip_max_attempts": 6,
    "register_max_per_window": 2,
}


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with running_app(RELAXED_LIMITS) as app:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            yield http


@pytest_asyncio.fixture
async def strict_client() -> AsyncIterator[httpx.AsyncClient]:
    """Tight rate limits, and a random client IP per test so counters never collide."""
    ip = ".".join(str(random.randint(1, 254)) for _ in range(4))
    async with running_app(STRICT_LIMITS) as app:
        transport = httpx.ASGITransport(app=app, client=(ip, 50_000))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            yield http


@pytest_asyncio.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """Direct database access for tests that must bypass the API (e.g. tampering attempts)."""
    settings: Settings = get_settings()
    engine = create_engine(settings)
    yield engine
    await engine.dispose()
