from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.models.identity import User
from app.schemas.user import UserCreate
from app.services.audit import record_audit
from app.services.auth import _hash, email_exists


async def create_user(
    session: AsyncSession, admin: User, data: UserCreate, ip_address: str | None
) -> User:
    """Admin adds a teammate to their own organization."""
    email = data.email.lower()
    if await email_exists(session, email):
        raise ConflictError("email already registered")

    user = User(
        organization_id=admin.organization_id,
        email=email,
        password_hash=await _hash(data.password),
        full_name=data.full_name,
        role=data.role.value,
    )
    session.add(user)
    await session.flush()
    record_audit(
        session,
        organization_id=admin.organization_id,
        actor_id=admin.id,
        action="user.created",
        resource_type="user",
        resource_id=str(user.id),
        details={"email": email, "role": data.role.value},
        ip_address=ip_address,
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("email already registered") from exc
    return user


async def list_users(session: AsyncSession, organization_id: object) -> list[User]:
    result = await session.execute(
        select(User).where(User.organization_id == organization_id).order_by(User.created_at)
    )
    return list(result.scalars())
