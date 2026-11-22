import asyncio
import re
import secrets
import time
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AuthenticationError, ConflictError
from app.core.security import (
    TokenClaims,
    TokenType,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import Role
from app.models.identity import Organization, User
from app.schemas.auth import RegisterRequest, TokenPair
from app.services.audit import record_audit
from app.services.token_store import REASON_LOGOUT, REASON_ROTATED, TokenStore


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "item"


@lru_cache
def _dummy_hash() -> str:
    return hash_password("timing-equalizer-not-a-real-password")


async def _hash(password: str) -> str:
    # Argon2 is deliberately slow (CPU-bound); run it off the event loop.
    return await asyncio.to_thread(hash_password, password)


async def email_exists(session: AsyncSession, email: str) -> bool:
    result = await session.execute(select(User.id).where(User.email == email))
    return result.first() is not None


async def register_organization(
    session: AsyncSession, data: RegisterRequest, ip_address: str | None
) -> User:
    """Create a new organization and its first user, who becomes admin."""
    email = data.email.lower()
    if await email_exists(session, email):
        raise ConflictError("email already registered")

    org = Organization(
        name=data.organization_name,
        slug=f"{slugify(data.organization_name)}-{secrets.token_hex(3)}",
    )
    session.add(org)
    await session.flush()  # assigns org.id

    user = User(
        organization_id=org.id,
        email=email,
        password_hash=await _hash(data.password),
        full_name=data.full_name,
        role=Role.ADMIN.value,
    )
    session.add(user)
    await session.flush()

    record_audit(
        session,
        organization_id=org.id,
        actor_id=user.id,
        action="organization.registered",
        resource_type="organization",
        resource_id=str(org.id),
        ip_address=ip_address,
    )
    try:
        await session.commit()
    except IntegrityError as exc:  # lost a race with a concurrent registration
        await session.rollback()
        raise ConflictError("email already registered") from exc
    return user


async def authenticate(
    session: AsyncSession, email: str, password: str, ip_address: str | None
) -> User:
    result = await session.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    # Verify against a dummy hash for unknown emails so response time doesn't reveal
    # which emails exist. The error message is identical for every failure.
    stored_hash = user.password_hash if user else _dummy_hash()
    password_ok = await asyncio.to_thread(verify_password, stored_hash, password)
    if user is None or not password_ok or not user.is_active:
        raise AuthenticationError("invalid email or password")

    record_audit(
        session,
        organization_id=user.organization_id,
        actor_id=user.id,
        action="auth.login",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
    )
    await session.commit()
    return user


def issue_tokens(user: User, settings: Settings) -> TokenPair:
    return TokenPair(
        access_token=create_token(user.id, TokenType.ACCESS, settings),
        refresh_token=create_token(user.id, TokenType.REFRESH, settings),
        expires_in=settings.access_token_minutes * 60,
    )


def _remaining_seconds(claims: TokenClaims) -> int:
    return int(claims.expires_at - time.time()) + 1


async def refresh_tokens(
    session: AsyncSession,
    token_store: TokenStore,
    refresh_token: str,
    settings: Settings,
    ip_address: str | None,
) -> TokenPair:
    """Exchange a refresh token for a new pair. Refresh tokens are single-use (rotation).

    Presenting an already-used refresh token means two parties hold the same token, which is
    what a theft looks like. We can't tell which one is the thief, so we revoke the user's
    sessions entirely and force a fresh login.
    """
    claims = decode_token(refresh_token, TokenType.REFRESH, settings)

    cutoff = await token_store.revoked_before(claims.user_id)
    if cutoff is not None and claims.issued_at < cutoff:
        raise AuthenticationError("session has been revoked")

    previous_reason = await token_store.revoke_token(
        claims.jti, _remaining_seconds(claims), REASON_ROTATED
    )
    if previous_reason == REASON_LOGOUT:
        raise AuthenticationError("session has been ended")  # stale client, not an attack
    user = await session.get(User, claims.user_id)

    if previous_reason is not None:  # a rotated token came back: treat as theft
        await token_store.revoke_all_for_user(claims.user_id, settings)
        if user is not None:
            record_audit(
                session,
                organization_id=user.organization_id,
                actor_id=user.id,
                action="auth.refresh_reuse_detected",
                resource_type="user",
                resource_id=str(user.id),
                ip_address=ip_address,
            )
            await session.commit()
        raise AuthenticationError("refresh token already used; all sessions revoked")

    if user is None or not user.is_active:
        raise AuthenticationError("invalid or expired token")
    return issue_tokens(user, settings)


async def logout(
    session: AsyncSession,
    token_store: TokenStore,
    refresh_token: str,
    settings: Settings,
    ip_address: str | None,
) -> None:
    """Revoke one refresh token (this device's session). Idempotent: never reveals whether
    the token was valid. The access token stays usable until it expires in minutes; to kill
    that too, use logout_all."""
    try:
        claims = decode_token(refresh_token, TokenType.REFRESH, settings)
    except AuthenticationError:
        return
    await token_store.revoke_token(claims.jti, _remaining_seconds(claims), REASON_LOGOUT)
    user = await session.get(User, claims.user_id)
    if user is not None:
        record_audit(
            session,
            organization_id=user.organization_id,
            actor_id=user.id,
            action="auth.logout",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        await session.commit()


async def logout_all(
    session: AsyncSession,
    token_store: TokenStore,
    user: User,
    settings: Settings,
    ip_address: str | None,
) -> None:
    """Invalidate every access and refresh token this user holds, on every device."""
    await token_store.revoke_all_for_user(user.id, settings)
    record_audit(
        session,
        organization_id=user.organization_id,
        actor_id=user.id,
        action="auth.logout_all",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
    )
    await session.commit()
