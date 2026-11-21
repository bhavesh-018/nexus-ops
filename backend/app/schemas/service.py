import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.enums import (
    Environment,
    MetricName,
    Operator,
    ServiceStatus,
    Severity,
    Tier,
)


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    environment: Environment
    tier: Tier = Tier.TIER2
    health_url: HttpUrl | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    environment: Environment | None = None
    tier: Tier | None = None
    health_url: HttpUrl | None = None
    metadata: dict[str, Any] | None = None


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str
    environment: Environment
    tier: Tier
    status: ServiceStatus
    health_url: str | None
    metadata: dict[str, Any] = Field(validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


class MonitoringConfigCreate(BaseModel):
    metric_name: MetricName
    operator: Operator
    threshold_value: float
    window_seconds: int = Field(gt=0, le=86_400)
    severity: Severity
    enabled: bool = True


class MonitoringConfigUpdate(BaseModel):
    operator: Operator | None = None
    threshold_value: float | None = None
    window_seconds: int | None = Field(default=None, gt=0, le=86_400)
    enabled: bool | None = None


class MonitoringConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID
    metric_name: MetricName
    operator: Operator
    threshold_value: float
    window_seconds: int
    severity: Severity
    enabled: bool
