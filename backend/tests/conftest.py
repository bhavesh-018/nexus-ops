import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from redis.asyncio import Redis

from app.core.config import get_settings
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


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """HTTP client wired to the real app, Postgres and Redis (integration tests only)."""
    settings = get_settings()
    app = create_app()
    app.state.engine = create_engine(settings)
    app.state.session_factory = create_session_factory(app.state.engine)
    app.state.redis = Redis.from_url(settings.redis_url)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    await app.state.redis.aclose()
    await app.state.engine.dispose()
