import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings
from app.core.errors import AuthenticationError

_hasher = PasswordHasher()  # Argon2id with safe defaults


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):  # mismatch subclasses VerificationError
        return False


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def create_token(
    user_id: uuid.UUID,
    token_type: TokenType,
    settings: Settings,
    now: datetime | None = None,
) -> str:
    """Signed JWT. Holds only who (sub) and what kind (type), never the role:
    the role is read from the database on each request so changes apply immediately."""
    now = now or datetime.now(UTC)
    lifetime = (
        timedelta(minutes=settings.access_token_minutes)
        if token_type is TokenType.ACCESS
        else timedelta(days=settings.refresh_token_days)
    )
    payload = {
        "sub": str(user_id),
        "type": token_type.value,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected: TokenType, settings: Settings) -> uuid.UUID:
    """Return the user id, or raise AuthenticationError (bad signature, expired, wrong type)."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "type"]},
        )
        if payload["type"] != expected.value:
            raise AuthenticationError("wrong token type")
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError) as exc:
        raise AuthenticationError("invalid or expired token") from exc
