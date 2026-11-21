from enum import StrEnum


class Role(StrEnum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


_ROLE_RANK = {Role.VIEWER: 1, Role.OPERATOR: 2, Role.ADMIN: 3}


def has_role(user_role: str, minimum: Role) -> bool:
    """True if user_role is at least `minimum` (admin > operator > viewer)."""
    try:
        return _ROLE_RANK[Role(user_role)] >= _ROLE_RANK[minimum]
    except ValueError:
        return False


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Tier(StrEnum):
    TIER1 = "tier1"  # revenue-critical
    TIER2 = "tier2"
    TIER3 = "tier3"


class ServiceStatus(StrEnum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class MetricName(StrEnum):
    CPU_PERCENT = "cpu_percent"
    MEMORY_PERCENT = "memory_percent"
    NETWORK_IN_BYTES = "network_in_bytes"
    NETWORK_OUT_BYTES = "network_out_bytes"
    LATENCY_P95_MS = "latency_p95_ms"
    ERROR_RATE_PERCENT = "error_rate_percent"
    AVAILABILITY_PERCENT = "availability_percent"


class Operator(StrEnum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
