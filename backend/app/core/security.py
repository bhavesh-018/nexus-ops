import uuid
from dataclasses import dataclass
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


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    jti: str  # unique id of this one token; lets us revoke it individually
    issued_at: float  # unix seconds, fractional (so "revoke everything before now" is exact)
    expires_at: float


def create_token(
    user_id: uuid.UUID,
    token_type: TokenType,
    settings: Settings,
    now: datetime | None = None,
) -> str:
    """Signed JWT. Holds who (sub), what kind (type) and which token (jti), never the role:
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
        "jti": uuid.uuid4().hex,
        "iat": now.timestamp(),
        "exp": now + lifetime,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected: TokenType, settings: Settings) -> TokenClaims:
    """Return the claims, or raise AuthenticationError (bad signature, expired, wrong type)."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "type", "jti", "iat"]},
        )
        if payload["type"] != expected.value:
            raise AuthenticationError("wrong token type")
        return TokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            jti=str(payload["jti"]),
            issued_at=float(payload["iat"]),
            expires_at=float(payload["exp"]),
        )
    except (jwt.PyJWTError, ValueError) as exc:
        raise AuthenticationError("invalid or expired token") from exc
