import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.identity import User
from app.models.service import MonitoringConfig, Service
from app.schemas.service import (
    MonitoringConfigCreate,
    MonitoringConfigUpdate,
    ServiceCreate,
    ServiceUpdate,
)
from app.services.audit import record_audit
from app.services.auth import slugify


async def _commit_or_conflict(session: AsyncSession, message: str) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(message) from exc


# ---- services ---------------------------------------------------------------


async def get_service(
    session: AsyncSession, organization_id: uuid.UUID, service_id: uuid.UUID
) -> Service:
    """Always scoped by organization: another tenant's id looks like it doesn't exist."""
    result = await session.execute(
        select(Service).where(Service.id == service_id, Service.organization_id == organization_id)
    )
    service = result.scalar_one_or_none()
    if service is None:
        raise NotFoundError("service not found")
    return service


async def list_services(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    environment: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> list[Service]:
    query = select(Service).where(Service.organization_id == organization_id)
    if environment:
        query = query.where(Service.environment == environment)
    if status:
        query = query.where(Service.status == status)
    query = query.order_by(Service.name).limit(limit).offset(offset)
    return list((await session.execute(query)).scalars())


async def create_service(
    session: AsyncSession, actor: User, data: ServiceCreate, ip_address: str | None
) -> Service:
    service = Service(
        organization_id=actor.organization_id,
        name=data.name,
        slug=slugify(data.name),
        environment=data.environment.value,
        tier=data.tier.value,
        health_url=str(data.health_url) if data.health_url else None,
        metadata_=data.metadata,
    )
    session.add(service)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("a service with this name already exists") from exc
    record_audit(
        session,
        organization_id=actor.organization_id,
        actor_id=actor.id,
        action="service.created",
        resource_type="service",
        resource_id=str(service.id),
        details={"name": service.name, "environment": service.environment},
        ip_address=ip_address,
    )
    await _commit_or_conflict(session, "a service with this name already exists")
    await session.refresh(service)  # load server-generated created_at/updated_at
    return service


async def update_service(
    session: AsyncSession,
    actor: User,
    service_id: uuid.UUID,
    data: ServiceUpdate,
    ip_address: str | None,
) -> Service:
    service = await get_service(session, actor.organization_id, service_id)
    changes = data.model_dump(exclude_unset=True, mode="json")
    if "name" in changes and changes["name"] is not None:
        service.name = changes["name"]
        service.slug = slugify(changes["name"])
    if "environment" in changes and changes["environment"] is not None:
        service.environment = changes["environment"]
    if "tier" in changes and changes["tier"] is not None:
        service.tier = changes["tier"]
    if "health_url" in changes:
        service.health_url = changes["health_url"]
    if "metadata" in changes and changes["metadata"] is not None:
        service.metadata_ = changes["metadata"]

    record_audit(
        session,
        organization_id=actor.organization_id,
        actor_id=actor.id,
        action="service.updated",
        resource_type="service",
        resource_id=str(service.id),
        details={"changed_fields": sorted(changes)},
        ip_address=ip_address,
    )
    await _commit_or_conflict(session, "a service with this name already exists")
    await session.refresh(service)
    return service


async def delete_service(
    session: AsyncSession, actor: User, service_id: uuid.UUID, ip_address: str | None
) -> None:
    service = await get_service(session, actor.organization_id, service_id)
    record_audit(
        session,
        organization_id=actor.organization_id,
        actor_id=actor.id,
        action="service.deleted",
        resource_type="service",
        resource_id=str(service.id),
        details={"name": service.name},
        ip_address=ip_address,
    )
    await session.delete(service)  # monitoring configs go with it (ON DELETE CASCADE)
    await session.commit()


# ---- monitoring configs ----------------------------------------------------


async def _get_config(
    session: AsyncSession, service_id: uuid.UUID, config_id: uuid.UUID
) -> MonitoringConfig:
    result = await session.execute(
        select(MonitoringConfig).where(
            MonitoringConfig.id == config_id, MonitoringConfig.service_id == service_id
        )
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise NotFoundError("monitoring config not found")
    return config


async def list_configs(
    session: AsyncSession, organization_id: uuid.UUID, service_id: uuid.UUID
) -> list[MonitoringConfig]:
    await get_service(session, organization_id, service_id)  # tenant check
    result = await session.execute(
        select(MonitoringConfig)
        .where(MonitoringConfig.service_id == service_id)
        .order_by(MonitoringConfig.metric_name, MonitoringConfig.severity)
    )
    return list(result.scalars())


async def create_config(
    session: AsyncSession,
    actor: User,
    service_id: uuid.UUID,
    data: MonitoringConfigCreate,
    ip_address: str | None,
) -> MonitoringConfig:
    await get_service(session, actor.organization_id, service_id)
    config = MonitoringConfig(
        service_id=service_id,
        metric_name=data.metric_name.value,
        operator=data.operator.value,
        threshold_value=data.threshold_value,
        window_seconds=data.window_seconds,
        severity=data.severity.value,
        enabled=data.enabled,
    )
    session.add(config)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("a rule for this metric and severity already exists") from exc
    record_audit(
        session,
        organization_id=actor.organization_id,
        actor_id=actor.id,
        action="monitoring_config.created",
        resource_type="monitoring_config",
        resource_id=str(config.id),
        details={
            "service_id": str(service_id),
            "metric_name": config.metric_name,
            "severity": config.severity,
        },
        ip_address=ip_address,
    )
    await session.commit()
    return config


async def update_config(
    session: AsyncSession,
    actor: User,
    service_id: uuid.UUID,
    config_id: uuid.UUID,
    data: MonitoringConfigUpdate,
    ip_address: str | None,
) -> MonitoringConfig:
    await get_service(session, actor.organization_id, service_id)
    config = await _get_config(session, service_id, config_id)
    changes = data.model_dump(exclude_unset=True, mode="json")
    for field, value in changes.items():
        if value is not None:
            setattr(config, field, value)
    record_audit(
        session,
        organization_id=actor.organization_id,
        actor_id=actor.id,
        action="monitoring_config.updated",
        resource_type="monitoring_config",
        resource_id=str(config.id),
        details={"changed_fields": sorted(changes)},
        ip_address=ip_address,
    )
    await session.commit()
    return config


async def delete_config(
    session: AsyncSession,
    actor: User,
    service_id: uuid.UUID,
    config_id: uuid.UUID,
    ip_address: str | None,
) -> None:
    await get_service(session, actor.organization_id, service_id)
    config = await _get_config(session, service_id, config_id)
    record_audit(
        session,
        organization_id=actor.organization_id,
        actor_id=actor.id,
        action="monitoring_config.deleted",
        resource_type="monitoring_config",
        resource_id=str(config.id),
        details={"service_id": str(service_id), "metric_name": config.metric_name},
        ip_address=ip_address,
    )
    await session.delete(config)
    await session.commit()
