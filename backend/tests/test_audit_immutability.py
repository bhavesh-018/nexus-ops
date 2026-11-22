"""The audit_logs table must refuse tampering at the database level.

Destructive attempts run inside a transaction that is always rolled back, so even if a guard
were broken these tests could not damage the data.
"""

import os
import uuid

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.helpers import add_user, register_org

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1", reason="set RUN_INTEGRATION=1 to run"
)


async def expect_rejected(engine: AsyncEngine, statement: str, params: dict[str, object]) -> None:
    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            with pytest.raises(DBAPIError, match="append-only"):
                await conn.execute(text(statement), params)
        finally:
            await trans.rollback()


async def org_id_of(client: httpx.AsyncClient, headers: dict[str, str]) -> uuid.UUID:
    me = await client.get("/api/v1/auth/me", headers=headers)
    return uuid.UUID(me.json()["organization_id"])


async def test_audit_rows_cannot_be_updated_deleted_or_truncated(
    client: httpx.AsyncClient, db_engine: AsyncEngine
) -> None:
    admin = await register_org(client)
    org_id = await org_id_of(client, admin.headers)

    await expect_rejected(
        db_engine,
        "UPDATE audit_logs SET action = 'tampered' WHERE organization_id = :org",
        {"org": org_id},
    )
    await expect_rejected(
        db_engine,
        "UPDATE audit_logs SET details = '{}'::jsonb WHERE organization_id = :org",
        {"org": org_id},
    )
    await expect_rejected(
        db_engine, "DELETE FROM audit_logs WHERE organization_id = :org", {"org": org_id}
    )
    await expect_rejected(db_engine, "TRUNCATE audit_logs", {})

    # Nothing was lost.
    logs = await client.get("/api/v1/audit-logs", headers=admin.headers)
    assert "organization.registered" in [e["action"] for e in logs.json()]


async def test_history_survives_deleting_the_user_who_acted(
    client: httpx.AsyncClient, db_engine: AsyncEngine
) -> None:
    admin = await register_org(client)
    operator = await add_user(client, admin, "operator")  # login writes an audit row for them
    me = await client.get("/api/v1/auth/me", headers=operator.headers)
    operator_id = uuid.UUID(me.json()["id"])

    # The FK is ON DELETE SET NULL: the guard must allow exactly that and nothing more.
    async with db_engine.begin() as conn:
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": operator_id})

    async with db_engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT actor_id FROM audit_logs "
                    "WHERE resource_id = :rid AND action = 'auth.login'"
                ),
                {"rid": str(operator_id)},
            )
        ).all()
    assert rows, "audit history was deleted along with the user"
    assert all(row.actor_id is None for row in rows)


async def test_deleting_a_whole_organization_still_works(
    client: httpx.AsyncClient, db_engine: AsyncEngine
) -> None:
    admin = await register_org(client)
    org_id = await org_id_of(client, admin.headers)

    async with db_engine.begin() as conn:
        await conn.execute(text("DELETE FROM organizations WHERE id = :id"), {"id": org_id})

    async with db_engine.connect() as conn:
        remaining = (
            await conn.execute(
                text("SELECT count(*) FROM audit_logs WHERE organization_id = :id"), {"id": org_id}
            )
        ).scalar_one()
    assert remaining == 0  # cascade is the one legitimate way audit rows disappear
