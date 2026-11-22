"""Service registry, monitoring configs, RBAC, tenant isolation and audit logging."""

import os

import httpx
import pytest

from tests.helpers import add_user, create_service, register_org

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1", reason="set RUN_INTEGRATION=1 to run"
)

RULE = {
    "metric_name": "error_rate_percent",
    "operator": "gt",
    "threshold_value": 5,
    "window_seconds": 60,
    "severity": "critical",
}


async def test_service_crud_lifecycle(client: httpx.AsyncClient) -> None:
    admin = await register_org(client)
    created = await create_service(client, admin, "Payment Service")
    assert created["slug"] == "payment-service"
    assert created["status"] == "unknown"  # no telemetry yet

    fetched = await client.get(f"/api/v1/services/{created['id']}", headers=admin.headers)
    assert fetched.status_code == 200

    patched = await client.patch(
        f"/api/v1/services/{created['id']}",
        headers=admin.headers,
        json={"tier": "tier3", "health_url": "http://payment:8080/health"},
    )
    assert patched.status_code == 200
    assert patched.json()["tier"] == "tier3"
    assert patched.json()["health_url"].startswith("http://payment:8080")

    listed = await client.get("/api/v1/services?environment=production", headers=admin.headers)
    assert [s["id"] for s in listed.json()] == [created["id"]]

    deleted = await client.delete(f"/api/v1/services/{created['id']}", headers=admin.headers)
    assert deleted.status_code == 204
    gone = await client.get(f"/api/v1/services/{created['id']}", headers=admin.headers)
    assert gone.status_code == 404


async def test_duplicate_service_name_conflicts_within_org_only(
    client: httpx.AsyncClient,
) -> None:
    admin = await register_org(client)
    await create_service(client, admin, "orders")
    dup = await client.post(
        "/api/v1/services",
        headers=admin.headers,
        json={"name": "Orders", "environment": "staging"},  # same slug
    )
    assert dup.status_code == 409

    other_org_admin = await register_org(client, "Other Org")
    await create_service(client, other_org_admin, "orders")  # allowed in another tenant


async def test_invalid_input_is_rejected(client: httpx.AsyncClient) -> None:
    admin = await register_org(client)
    resp = await client.post(
        "/api/v1/services", headers=admin.headers, json={"name": "x", "environment": "mars"}
    )
    assert resp.status_code == 422


async def test_tenant_isolation(client: httpx.AsyncClient) -> None:
    org_a = await register_org(client, "Org A")
    org_b = await register_org(client, "Org B")
    service = await create_service(client, org_a, "secret-service")

    # Org B can't see, change, delete or list Org A's service; it looks like it doesn't exist.
    sid = service["id"]
    url = f"/api/v1/services/{sid}"
    assert (await client.get(url, headers=org_b.headers)).status_code == 404
    patch = await client.patch(url, headers=org_b.headers, json={"tier": "tier3"})
    assert patch.status_code == 404
    assert (await client.delete(url, headers=org_b.headers)).status_code == 404
    assert (await client.get("/api/v1/services", headers=org_b.headers)).json() == []
    rules = await client.get(f"/api/v1/services/{sid}/monitoring-configs", headers=org_b.headers)
    assert rules.status_code == 404


async def test_rbac_matrix(client: httpx.AsyncClient) -> None:
    admin = await register_org(client)
    operator = await add_user(client, admin, "operator")
    viewer = await add_user(client, admin, "viewer")
    service = await create_service(client, admin)
    new_service = {"name": "inventory", "environment": "production"}

    # Everyone in the org can read.
    for account in (admin, operator, viewer):
        resp = await client.get("/api/v1/services", headers=account.headers)
        assert resp.status_code == 200

    # Only admins can write.
    for account in (operator, viewer):
        assert (
            await client.post("/api/v1/services", headers=account.headers, json=new_service)
        ).status_code == 403
        assert (
            await client.delete(f"/api/v1/services/{service['id']}", headers=account.headers)
        ).status_code == 403
        assert (
            await client.post(
                f"/api/v1/services/{service['id']}/monitoring-configs",
                headers=account.headers,
                json=RULE,
            )
        ).status_code == 403

    # Admin-only management endpoints.
    for account in (operator, viewer):
        assert (await client.get("/api/v1/users", headers=account.headers)).status_code == 403
        assert (await client.get("/api/v1/audit-logs", headers=account.headers)).status_code == 403
    assert (await client.get("/api/v1/users", headers=admin.headers)).status_code == 200


async def test_monitoring_config_crud_and_uniqueness(client: httpx.AsyncClient) -> None:
    admin = await register_org(client)
    service = await create_service(client, admin)
    base = f"/api/v1/services/{service['id']}/monitoring-configs"

    created = await client.post(base, headers=admin.headers, json=RULE)
    assert created.status_code == 201
    config_id = created.json()["id"]

    dup = await client.post(base, headers=admin.headers, json=RULE)
    assert dup.status_code == 409  # same metric + severity

    patched = await client.patch(
        f"{base}/{config_id}", headers=admin.headers, json={"threshold_value": 10, "enabled": False}
    )
    assert patched.status_code == 200
    assert patched.json()["threshold_value"] == 10
    assert patched.json()["enabled"] is False

    bad = await client.post(base, headers=admin.headers, json={**RULE, "window_seconds": 0})
    assert bad.status_code == 422

    listed = await client.get(base, headers=admin.headers)
    assert len(listed.json()) == 1

    assert (await client.delete(f"{base}/{config_id}", headers=admin.headers)).status_code == 204
    assert (await client.get(base, headers=admin.headers)).json() == []


async def test_deleting_service_removes_its_configs(client: httpx.AsyncClient) -> None:
    admin = await register_org(client)
    service = await create_service(client, admin)
    base = f"/api/v1/services/{service['id']}/monitoring-configs"
    await client.post(base, headers=admin.headers, json=RULE)
    assert (
        await client.delete(f"/api/v1/services/{service['id']}", headers=admin.headers)
    ).status_code == 204
    assert (await client.get(base, headers=admin.headers)).status_code == 404


async def test_audit_log_records_changes(client: httpx.AsyncClient) -> None:
    admin = await register_org(client)
    service = await create_service(client, admin, "billing")
    await client.patch(
        f"/api/v1/services/{service['id']}", headers=admin.headers, json={"tier": "tier3"}
    )
    await client.post(
        f"/api/v1/services/{service['id']}/monitoring-configs", headers=admin.headers, json=RULE
    )
    await client.delete(f"/api/v1/services/{service['id']}", headers=admin.headers)

    logs = await client.get("/api/v1/audit-logs?limit=100", headers=admin.headers)
    assert logs.status_code == 200
    actions = [entry["action"] for entry in logs.json()]
    for expected in (
        "organization.registered",
        "service.created",
        "service.updated",
        "monitoring_config.created",
        "service.deleted",
    ):
        assert expected in actions

    filtered = await client.get("/api/v1/audit-logs?action=service.created", headers=admin.headers)
    assert [e["action"] for e in filtered.json()] == ["service.created"]
    assert filtered.json()[0]["actor_id"] is not None


async def test_audit_logs_are_tenant_scoped(client: httpx.AsyncClient) -> None:
    org_a = await register_org(client, "Org A")
    org_b = await register_org(client, "Org B")
    await create_service(client, org_a, "only-in-a")
    logs_b = await client.get("/api/v1/audit-logs?limit=100", headers=org_b.headers)
    assert "service.created" not in [e["action"] for e in logs_b.json()]
