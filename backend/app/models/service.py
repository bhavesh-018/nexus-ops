import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, UUIDPrimaryKey, check_in
from app.models.enums import (
    Environment,
    MetricName,
    Operator,
    ServiceStatus,
    Severity,
    Tier,
)


class Service(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "services"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_services_org_slug"),
        check_in("environment", Environment, "environment"),
        check_in("tier", Tier, "tier"),
        check_in("status", ServiceStatus, "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100))  # derived from name, unique per org
    environment: Mapped[str] = mapped_column(String(20))
    tier: Mapped[str] = mapped_column(String(20))
    # Written by the telemetry worker from Phase 3; "unknown" until telemetry arrives.
    status: Mapped[str] = mapped_column(
        String(20), default=ServiceStatus.UNKNOWN.value, server_default="unknown"
    )
    health_url: Mapped[str | None] = mapped_column(String(2048))
    # "metadata" is reserved by SQLAlchemy's declarative base, hence the attribute rename.
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MonitoringConfig(UUIDPrimaryKey, Base):
    """One alert rule: e.g. error_rate_percent > 5 for 60s => critical."""

    __tablename__ = "monitoring_configs"
    __table_args__ = (
        UniqueConstraint(
            "service_id",
            "metric_name",
            "severity",
            name="uq_monitoring_configs_service_metric_severity",
        ),
        check_in("metric_name", MetricName, "metric_name"),
        check_in("operator", Operator, "operator"),
        check_in("severity", Severity, "severity"),
        CheckConstraint("window_seconds > 0", name="window_positive"),
    )

    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), index=True
    )
    metric_name: Mapped[str] = mapped_column(String(50))
    operator: Mapped[str] = mapped_column(String(5))
    threshold_value: Mapped[float] = mapped_column(Float)
    window_seconds: Mapped[int] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(20))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
