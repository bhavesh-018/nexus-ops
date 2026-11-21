"""Integration tests against real PostgreSQL and Redis.

Skipped unless RUN_INTEGRATION=1 (CI sets it; locally run `docker compose up -d` first).
"""

import os

import httpx
import pytest
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import create_engine
from app.main import create_app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1", reason="set RUN_INTEGRATION=1 to run"
)


async def test_ready_against_real_services() -> None:
    settings = get_settings()
    app = create_app()
    app.state.engine = create_engine(settings)
    app.state.redis = Redis.from_url(settings.redis_url)
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ready")
        assert resp.status_code == 200
        assert resp.json()["checks"] == {"database": True, "redis": True}
    finally:
        await app.state.redis.aclose()
        await app.state.engine.dispose()


async def test_pgvector_extension_is_available() -> None:
    engine = create_engine(get_settings())
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
            )
        assert result.scalar() == 1
    finally:
        await engine.dispose()
