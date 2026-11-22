import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.core.security import (
    TokenType,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import Role, has_role
from app.schemas.auth import RegisterRequest
from app.schemas.service import MonitoringConfigCreate
from app.services.auth import slugify


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "redis_url": "redis://localhost:6379/0",
        "jwt_secret": "x" * 40,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("correct-horse-battery")
    assert hashed != "correct-horse-battery"
    assert verify_password(hashed, "correct-horse-battery")
    assert not verify_password(hashed, "wrong-password-here")


def test_verify_password_rejects_garbage_hash() -> None:
    assert not verify_password("not-a-real-hash", "anything")


def test_token_roundtrip() -> None:
    settings = make_settings()
    user_id = uuid.uuid4()
    token = create_token(user_id, TokenType.ACCESS, settings)
    claims = decode_token(token, TokenType.ACCESS, settings)
    assert claims.user_id == user_id
    assert claims.expires_at > claims.issued_at


def test_every_token_has_a_unique_id() -> None:
    settings = make_settings()
    user_id = uuid.uuid4()
    refresh = TokenType.REFRESH
    first = decode_token(create_token(user_id, refresh, settings), refresh, settings)
    second = decode_token(create_token(user_id, refresh, settings), refresh, settings)
    assert first.jti != second.jti


def test_refresh_token_cannot_be_used_as_access_token() -> None:
    settings = make_settings()
    token = create_token(uuid.uuid4(), TokenType.REFRESH, settings)
    with pytest.raises(AuthenticationError):
        decode_token(token, TokenType.ACCESS, settings)


def test_expired_token_is_rejected() -> None:
    settings = make_settings()
    long_ago = datetime.now(UTC) - timedelta(days=30)
    token = create_token(uuid.uuid4(), TokenType.ACCESS, settings, now=long_ago)
    with pytest.raises(AuthenticationError):
        decode_token(token, TokenType.ACCESS, settings)


def test_token_signed_with_other_secret_is_rejected() -> None:
    token = create_token(uuid.uuid4(), TokenType.ACCESS, make_settings(jwt_secret="a" * 40))
    with pytest.raises(AuthenticationError):
        decode_token(token, TokenType.ACCESS, make_settings(jwt_secret="b" * 40))


def test_garbage_token_is_rejected() -> None:
    with pytest.raises(AuthenticationError):
        decode_token("nonsense", TokenType.ACCESS, make_settings())


def test_settings_reject_short_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        make_settings(jwt_secret="short")


@pytest.mark.parametrize(
    ("user_role", "minimum", "expected"),
    [
        ("admin", Role.ADMIN, True),
        ("admin", Role.VIEWER, True),
        ("operator", Role.OPERATOR, True),
        ("operator", Role.ADMIN, False),
        ("viewer", Role.OPERATOR, False),
        ("viewer", Role.VIEWER, True),
        ("bogus", Role.VIEWER, False),
    ],
)
def test_role_hierarchy(user_role: str, minimum: Role, expected: bool) -> None:
    assert has_role(user_role, minimum) is expected


def test_register_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            organization_name="Acme", email="a@example.com", password="short", full_name="A"
        )


def test_monitoring_config_rejects_unknown_metric_and_bad_window() -> None:
    base = {"operator": "gt", "threshold_value": 5, "window_seconds": 60, "severity": "critical"}
    MonitoringConfigCreate(metric_name="error_rate_percent", **base)  # valid
    with pytest.raises(ValidationError):
        MonitoringConfigCreate(metric_name="made_up_metric", **base)
    with pytest.raises(ValidationError):
        MonitoringConfigCreate(
            metric_name="cpu_percent", **{**base, "window_seconds": 0}  # type: ignore[arg-type]
        )


def test_slugify() -> None:
    assert slugify("Payment Service!") == "payment-service"
    assert slugify("!!!") == "item"
