import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import AdminUser, ClientIp, SessionDep, ViewerUser
from app.models.enums import Environment, ServiceStatus
from app.schemas.service import (
    MonitoringConfigCreate,
    MonitoringConfigOut,
    MonitoringConfigUpdate,
    ServiceCreate,
    ServiceOut,
    ServiceUpdate,
)
from app.services import service_registry as registry

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=list[ServiceOut])
async def list_services(
    user: ViewerUser,
    session: SessionDep,
    environment: Environment | None = None,
    status: ServiceStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ServiceOut]:
    services = await registry.list_services(
        session,
        user.organization_id,
        environment=environment.value if environment else None,
        status=status.value if status else None,
        limit=limit,
        offset=offset,
    )
    return [ServiceOut.model_validate(s) for s in services]


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
async def create_service(
    body: ServiceCreate, admin: AdminUser, session: SessionDep, ip: ClientIp
) -> ServiceOut:
    service = await registry.create_service(session, admin, body, ip)
    return ServiceOut.model_validate(service)


@router.get("/{service_id}", response_model=ServiceOut)
async def get_service(service_id: uuid.UUID, user: ViewerUser, session: SessionDep) -> ServiceOut:
    service = await registry.get_service(session, user.organization_id, service_id)
    return ServiceOut.model_validate(service)


@router.patch("/{service_id}", response_model=ServiceOut)
async def update_service(
    service_id: uuid.UUID,
    body: ServiceUpdate,
    admin: AdminUser,
    session: SessionDep,
    ip: ClientIp,
) -> ServiceOut:
    service = await registry.update_service(session, admin, service_id, body, ip)
    return ServiceOut.model_validate(service)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: uuid.UUID, admin: AdminUser, session: SessionDep, ip: ClientIp
) -> Response:
    await registry.delete_service(session, admin, service_id, ip)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- monitoring configs (alert thresholds), nested under a service ----------


@router.get("/{service_id}/monitoring-configs", response_model=list[MonitoringConfigOut])
async def list_configs(
    service_id: uuid.UUID, user: ViewerUser, session: SessionDep
) -> list[MonitoringConfigOut]:
    configs = await registry.list_configs(session, user.organization_id, service_id)
    return [MonitoringConfigOut.model_validate(c) for c in configs]


@router.post(
    "/{service_id}/monitoring-configs",
    response_model=MonitoringConfigOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_config(
    service_id: uuid.UUID,
    body: MonitoringConfigCreate,
    admin: AdminUser,
    session: SessionDep,
    ip: ClientIp,
) -> MonitoringConfigOut:
    config = await registry.create_config(session, admin, service_id, body, ip)
    return MonitoringConfigOut.model_validate(config)


@router.patch(
    "/{service_id}/monitoring-configs/{config_id}", response_model=MonitoringConfigOut
)
async def update_config(
    service_id: uuid.UUID,
    config_id: uuid.UUID,
    body: MonitoringConfigUpdate,
    admin: AdminUser,
    session: SessionDep,
    ip: ClientIp,
) -> MonitoringConfigOut:
    config = await registry.update_config(session, admin, service_id, config_id, body, ip)
    return MonitoringConfigOut.model_validate(config)


@router.delete(
    "/{service_id}/monitoring-configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_config(
    service_id: uuid.UUID,
    config_id: uuid.UUID,
    admin: AdminUser,
    session: SessionDep,
    ip: ClientIp,
) -> Response:
    await registry.delete_config(session, admin, service_id, config_id, ip)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
