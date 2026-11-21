"""Auth flows against the real app + Postgres. Needs RUN_INTEGRATION=1 and Docker infra up."""

import os

import httpx
import pytest

from tests.helpers import PASSWORD, register_org, unique_email

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1", reason="set RUN_INTEGRATION=1 to run"
)


async def test_register_login_and_me(client: httpx.AsyncClient) -> None:
    admin = await register_org(client)

    login = await client.post(
        "/api/v1/auth/login", json={"email": admin.email, "password": PASSWORD}
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"

    me = await client.get("/api/v1/auth/me", headers=admin.headers)
    assert me.status_code == 200
    assert me.json()["email"] == admin.email
    assert me.json()["role"] == "admin"  # first user of a new org is its admin
    assert "password" not in me.text


async def test_duplicate_email_is_rejected(client: httpx.AsyncClient) -> None:
    admin = await register_org(client)
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Other Org",
            "email": admin.email.upper(),  # emails are case-insensitive
            "password": PASSWORD,
            "full_name": "Dup",
        },
    )
    assert resp.status_code == 409


async def test_wrong_password_and_unknown_email_look_identical(
    client: httpx.AsyncClient,
) -> None:
    admin = await register_org(client)
    wrong_pw = await client.post(
        "/api/v1/auth/login", json={"email": admin.email, "password": "totally-wrong-pw"}
    )
    unknown = await client.post(
        "/api/v1/auth/login", json={"email": unique_email("ghost"), "password": PASSWORD}
    )
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()  # no user enumeration


async def test_protected_endpoint_requires_token(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    bad = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nonsense"})
    assert bad.status_code == 401
    assert bad.headers["www-authenticate"] == "Bearer"


async def test_refresh_flow_and_token_type_separation(client: httpx.AsyncClient) -> None:
    admin = await register_org(client)

    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": admin.refresh_token}
    )
    assert refreshed.status_code == 200
    new_access = refreshed.json()["access_token"]
    ok = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert ok.status_code == 200

    # An access token must not work as a refresh token, nor vice versa.
    bad_refresh = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": admin.access_token}
    )
    assert bad_refresh.status_code == 401
    refresh_as_access = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {admin.refresh_token}"}
    )
    assert refresh_as_access.status_code == 401
