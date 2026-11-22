"""Login and registration rate limiting (tight limits: 3 per IP+email, 6 per IP, 2 registers)."""

import os

import httpx
import pytest

from tests.helpers import PASSWORD, register_org, unique_email

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1", reason="set RUN_INTEGRATION=1 to run"
)


async def attempt(client: httpx.AsyncClient, email: str, password: str) -> httpx.Response:
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def test_repeated_failures_get_blocked_with_retry_after(
    strict_client: httpx.AsyncClient,
) -> None:
    admin = await register_org(strict_client)

    for _ in range(3):
        assert (await attempt(strict_client, admin.email, "wrong-password-1")).status_code == 401

    blocked = await attempt(strict_client, admin.email, "wrong-password-1")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
    assert 1 <= int(blocked.headers["retry-after"]) <= 900

    # While blocked, even the correct password is refused (that is the point).
    assert (await attempt(strict_client, admin.email, PASSWORD)).status_code == 429


async def test_successful_login_resets_the_counter(strict_client: httpx.AsyncClient) -> None:
    admin = await register_org(strict_client)

    for _ in range(2):
        assert (await attempt(strict_client, admin.email, "wrong-password-1")).status_code == 401
    assert (await attempt(strict_client, admin.email, PASSWORD)).status_code == 200

    # The counter restarted: two more mistakes are fine, no 429.
    for _ in range(2):
        assert (await attempt(strict_client, admin.email, "wrong-password-1")).status_code == 401


async def test_blocking_one_account_does_not_block_others(
    strict_client: httpx.AsyncClient,
) -> None:
    victim = await register_org(strict_client)
    other = await register_org(strict_client, "Other Org")

    for _ in range(4):
        await attempt(strict_client, victim.email, "wrong-password-1")
    assert (await attempt(strict_client, victim.email, "x" * 12)).status_code == 429

    assert (await attempt(strict_client, other.email, PASSWORD)).status_code == 200


async def test_one_ip_spraying_many_emails_is_blocked(strict_client: httpx.AsyncClient) -> None:
    # Each email is tried once, so the per-account limit never triggers; the per-IP cap does.
    statuses = [
        (await attempt(strict_client, unique_email("spray"), "wrong-password-1")).status_code
        for _ in range(8)
    ]
    assert statuses[:6] == [401] * 6
    assert statuses[6:] == [429, 429]


async def test_registration_is_rate_limited(strict_client: httpx.AsyncClient) -> None:
    for i in range(2):
        resp = await strict_client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": f"Org {i}",
                "email": unique_email("reg"),
                "password": PASSWORD,
                "full_name": "Reg Tester",
            },
        )
        assert resp.status_code == 201

    third = await strict_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Org 3",
            "email": unique_email("reg"),
            "password": PASSWORD,
            "full_name": "Reg Tester",
        },
    )
    assert third.status_code == 429
    assert "retry-after" in third.headers
