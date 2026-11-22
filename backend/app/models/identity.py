import uuid

from sqlalchemy import Boolean, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, UUIDPrimaryKey, check_in
from app.models.enums import Role


class Organization(UUIDPrimaryKey, CreatedAt, Base):
    """Tenant boundary: every other record belongs to exactly one organization."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True)


class User(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "users"
    __table_args__ = (check_in("role", Role, "role"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(320), unique=True)  # stored lowercase
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
