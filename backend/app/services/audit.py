import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


def record_audit(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Stage an audit row. The caller commits, so the change and its audit entry are atomic."""
    session.add(
        AuditLog(
            organization_id=organization_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
        )
    )


async def list_audit_logs(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    action: str | None,
    resource_type: str | None,
    limit: int,
    offset: int,
) -> list[AuditLog]:
    query = select(AuditLog).where(AuditLog.organization_id == organization_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    return list((await session.execute(query)).scalars())
