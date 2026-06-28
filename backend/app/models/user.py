"""
models/user.py — User model for the Pepto platform.

Roles:
    customer  — books services for their pets.
    provider  — offers pet services.
    admin     — platform administrator.
"""

from __future__ import annotations

import enum
import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Any, List, Optional

import jwt as pyjwt
from flask import current_app
from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import bcrypt, db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.provider import ProviderProfile
    from app.models.pet import Pet
    from app.models.booking import Booking


class UserRole(str, enum.Enum):
    """Enumerated roles for platform users."""

    customer = "customer"
    provider = "provider"
    admin = "admin"


# SQLAlchemy Enum type registered under the same name used in the DB column
_role_enum = Enum(
    UserRole,
    name="userrole",
    values_callable=lambda obj: [e.value for e in obj],
)


class User(BaseMixin, db.Model):
    """Represents a Pepto platform user (customer, provider, or admin).

    Attributes:
        email: Unique login identifier.
        phone: Optional phone number.
        password_hash: Bcrypt-hashed password (never expose in API responses).
        full_name: Display name.
        avatar_url: URL to the user's profile picture.
        role: One of customer / provider / admin.
        is_verified: True once email verification is complete.
        is_active: False for suspended accounts.
        last_login: Timestamp of most recent successful login.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        unique=False,
        index=True,
        nullable=True,
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    full_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    role: Mapped[UserRole] = mapped_column(
        _role_enum,
        nullable=False,
        default=UserRole.customer,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    provider_profile: Mapped[Optional["ProviderProfile"]] = relationship(
        "ProviderProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )

    pets: Mapped[List["Pet"]] = relationship(
        "Pet",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="select",
        foreign_keys="Pet.customer_id",
    )

    bookings_as_customer: Mapped[List["Booking"]] = relationship(
        "Booking",
        back_populates="customer",
        lazy="select",
        foreign_keys="Booking.customer_id",
    )

    # ── Password helpers ──────────────────────────────────────────────────────

    def set_password(self, raw_password: str) -> None:
        """Hash *raw_password* with bcrypt and store it.

        Args:
            raw_password: The plaintext password supplied by the user.
        """
        self.password_hash = bcrypt.generate_password_hash(raw_password).decode(
            "utf-8"
        )

    def check_password(self, raw_password: str) -> bool:
        """Verify *raw_password* against the stored hash.

        Args:
            raw_password: Candidate plaintext password.

        Returns:
            True if the password matches, False otherwise.
        """
        if not self.password_hash:
            return False
        return bcrypt.check_password_hash(self.password_hash, raw_password)

    # ── Token helpers ─────────────────────────────────────────────────────────

    def generate_verification_token(self) -> str:
        """Generate a signed JWT for email verification.

        Returns:
            A compact URL-safe JWT string, valid for 24 hours.
        """
        import time

        payload = {
            "sub": str(self.id),
            "purpose": "email_verification",
            "iat": int(time.time()),
            "exp": int(time.time()) + 86400,  # 24 h
        }
        secret = current_app.config.get("JWT_SECRET_KEY", "fallback-secret")
        return pyjwt.encode(payload, secret, algorithm="HS256")

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_public_dict(self) -> Dict[str, Any]:
        """Return a safe public representation (no password_hash).

        Returns:
            Dict suitable for API responses.
        """
        data = self.to_dict(exclude=["password_hash"])
        # Ensure role is the string value, not the enum object
        if isinstance(data.get("role"), UserRole):
            data["role"] = data["role"].value
        return data
