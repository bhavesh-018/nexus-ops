import uuid
from dataclasses import dataclass

import httpx

PASSWORD = "correct-horse-battery"


@dataclass
class Account:
    email: str
    password: str
    access_token: str
    refresh_token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


async def register_org(client: httpx.AsyncClient, org_name: str = "Acme Corp") -> Account:
    """Register a brand-new organization (its own tenant) and return the admin's session."""
    email = unique_email("admin")
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": org_name,
            "email": email,
            "password": PASSWORD,
            "full_name": "Ada Admin",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return Account(email, PASSWORD, body["access_token"], body["refresh_token"])


async def add_user(client: httpx.AsyncClient, admin: Account, role: str) -> Account:
    """Admin creates a teammate with `role`, who then logs in."""
    email = unique_email(role)
    resp = await client.post(
        "/api/v1/users",
        headers=admin.headers,
        json={"email": email, "password": PASSWORD, "full_name": f"Test {role}", "role": role},
    )
    assert resp.status_code == 201, resp.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    body = login.json()
    return Account(email, PASSWORD, body["access_token"], body["refresh_token"])


async def create_service(
    client: httpx.AsyncClient, admin: Account, name: str = "payment-service"
) -> dict:
    resp = await client.post(
        "/api/v1/services",
        headers=admin.headers,
        json={"name": name, "environment": "production", "tier": "tier1"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
