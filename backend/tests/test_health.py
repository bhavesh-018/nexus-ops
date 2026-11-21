import json
import logging

import httpx
import pytest

from app.core.logging import JsonFormatter
from app.main import create_app


class FakeRedis:
    def __init__(self, ok: bool) -> None:
        self.ok = ok

    async def ping(self) -> bool:
        if not self.ok:
            raise ConnectionError("redis down")
        return True


class FakeConn:
    def __init__(self, ok: bool) -> None:
        self.ok = ok

    async def __aenter__(self) -> "FakeConn":
        if not self.ok:
            raise ConnectionError("db down")
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def execute(self, *_: object) -> None:
        return None


class FakeEngine:
    def __init__(self, ok: bool) -> None:
        self.ok = ok

    def connect(self) -> FakeConn:
        return FakeConn(self.ok)


def make_client(db_ok: bool, redis_ok: bool) -> httpx.AsyncClient:
    app = create_app()
    app.state.engine = FakeEngine(db_ok)
    app.state.redis = FakeRedis(redis_ok)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_health_is_independent_of_dependencies() -> None:
    async with make_client(False, False) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_ready_when_all_dependencies_up() -> None:
    async with make_client(True, True) as client:
        resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["checks"] == {"database": True, "redis": True}


@pytest.mark.parametrize(
    ("db_ok", "redis_ok", "expected"),
    [
        (False, True, {"database": False, "redis": True}),
        (True, False, {"database": True, "redis": False}),
    ],
)
async def test_ready_returns_503_when_a_dependency_is_down(
    db_ok: bool, redis_ok: bool, expected: dict[str, bool]
) -> None:
    async with make_client(db_ok, redis_ok) as client:
        resp = await client.get("/ready")
    assert resp.status_code == 503
    assert resp.json()["status"] == "degraded"
    assert resp.json()["checks"] == expected


def test_json_formatter_emits_valid_json() -> None:
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello %s", ("world",), None)
    data = json.loads(JsonFormatter().format(record))
    assert data["message"] == "hello world"
    assert data["level"] == "INFO"
