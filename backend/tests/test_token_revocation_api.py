"""Refresh-token rotation, reuse detection, logout and logout-everywhere."""

import os

import httpx
import pytest

from tests.helpers import PASSWORD, Account, register_org

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1", reason="set RUN_INTEGRATION=1 to run"
)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def refresh(client: httpx.AsyncClient, refresh_token: str) -> httpx.Response:
    return await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})


async def login(client: httpx.AsyncClient, account: Account) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": account.email, "password": PASSWORD}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def audit_actions(client: httpx.AsyncClient, token: str) -> list[str]:
    resp = await client.get("/api/v1/audit-logs?limit=100", headers=bearer(token))
    assert resp.status_code == 200, resp.text
    return [entry["action"] for entry in resp.json()]


async def test_refresh_rotates_the_token(client: httpx.AsyncClient) -> None:
    admin = await register_org(client)

    first = await refresh(client, admin.refresh_token)
    assert first.status_code == 200
    new_pair = first.json()
    assert new_pair["refresh_token"] != admin.refresh_token

    # The new pair works, and can itself be exchanged once.
    me = await client.get("/api/v1/auth/me", headers=bearer(new_pair["access_token"]))
    assert me.status_code == 200
    assert (await refresh(client, new_pair["refresh_token"])).status_code == 200


async def test_reusing_a_refresh_token_revokes_every_session(client: httpx.AsyncClient) -> None:
    admin = await register_org(client)

    rotated = (await refresh(client, admin.refresh_token)).json()

    # Replaying the already-used token looks like theft: it must fail...
    replay = await refresh(client, admin.refresh_token)
    assert replay.status_code == 401

    # ...and take down the legitimate, newer session too (we can't tell who is who).
    assert (await refresh(client, rotated["refresh_token"])).status_code == 401
    still_valid = await client.get("/api/v1/auth/me", headers=bearer(rotated["access_token"]))
    assert still_valid.status_code == 401

    # A fresh login starts a clean session, and the incident is on the audit log.
    pair = await login(client, admin)
    assert "auth.refresh_reuse_detected" in await audit_actions(client, pair["access_token"])


async def test_logout_revokes_that_refresh_token(client: httpx.AsyncClient) -> None:
    admin = await register_org(client)

    out = await client.post("/api/v1/auth/logout", json={"refresh_token": admin.refresh_token})
    assert out.status_code == 204
    assert (await refresh(client, admin.refresh_token)).status_code == 401

    # Idempotent, and never reveals whether a token was valid.
    again = await client.post("/api/v1/auth/logout", json={"refresh_token": admin.refresh_token})
    assert again.status_code == 204
    junk = await client.post("/api/v1/auth/logout", json={"refresh_token": "nonsense"})
    assert junk.status_code == 204

    # Documented limit: a single logout kills the refresh token, not the short-lived access
    # token. Use logout-all to kill access tokens too.
    me = await client.get("/api/v1/auth/me", headers=admin.headers)
    assert me.status_code == 200


async def test_logout_of_one_device_leaves_other_devices_alone(
    client: httpx.AsyncClient,
) -> None:
    admin = await register_org(client)
    other_device = await login(client, admin)

    await client.post("/api/v1/auth/logout", json={"refresh_token": admin.refresh_token})
    # A stale client retries with its logged-out token: refused, but NOT treated as theft.
    assert (await refresh(client, admin.refresh_token)).status_code == 401

    assert (await refresh(client, other_device["refresh_token"])).status_code == 200


async def test_logout_all_ends_every_session(client: httpx.AsyncClient) -> None:
    admin = await register_org(client)
    second_device = await login(client, admin)

    out = await client.post("/api/v1/auth/logout-all", headers=admin.headers)
    assert out.status_code == 204

    for access, refresh_token in (
        (admin.access_token, admin.refresh_token),
        (second_device["access_token"], second_device["refresh_token"]),
    ):
        assert (await client.get("/api/v1/auth/me", headers=bearer(access))).status_code == 401
        assert (await refresh(client, refresh_token)).status_code == 401

    # Logging in again works and yields a usable session.
    fresh = await login(client, admin)
    assert (
        await client.get("/api/v1/auth/me", headers=bearer(fresh["access_token"]))
    ).status_code == 200
    assert "auth.logout_all" in await audit_actions(client, fresh["access_token"])


async def test_logout_all_only_affects_the_caller(client: httpx.AsyncClient) -> None:
    alice = await register_org(client, "Alice Org")
    bob = await register_org(client, "Bob Org")

    await client.post("/api/v1/auth/logout-all", headers=alice.headers)

    assert (await client.get("/api/v1/auth/me", headers=bob.headers)).status_code == 200
    assert (await refresh(client, bob.refresh_token)).status_code == 200


async def test_logout_all_requires_authentication(client: httpx.AsyncClient) -> None:
    assert (await client.post("/api/v1/auth/logout-all")).status_code == 401
