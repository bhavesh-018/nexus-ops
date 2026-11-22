from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, SessionDep
from app.schemas.audit import AuditLogOut
from app.services import audit as audit_service

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
async def list_audit_logs(
    admin: AdminUser,
    session: SessionDep,
    action: str | None = None,
    resource_type: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AuditLogOut]:
    logs = await audit_service.list_audit_logs(
        session,
        admin.organization_id,
        action=action,
        resource_type=resource_type,
        limit=limit,
        offset=offset,
    )
    return [AuditLogOut.model_validate(entry) for entry in logs]
