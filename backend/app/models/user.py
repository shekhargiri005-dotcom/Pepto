"""
models/user.py — User model for the Pepto Pet Food Delivery platform.

Roles:
    customer         — browses stores, places orders for pet food.
    store_owner      — manages a pet food store, products and incoming orders.
    delivery_partner — picks up and delivers orders to customers.
    admin            — platform administrator.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import jwt as pyjwt
from flask import current_app
from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import bcrypt, db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.store import Store
    from app.models.pet import Pet
    from app.models.order import Order
    from app.models.delivery_partner import DeliveryPartner


class UserRole(str, enum.Enum):
    """Enumerated roles for platform users."""

    customer = "customer"
    store_owner = "store_owner"
    delivery_partner = "delivery_partner"
    admin = "admin"


# SQLAlchemy Enum type registered under the same name used in the DB column
_role_enum = Enum(
    UserRole,
    name="userrole",
    values_callable=lambda obj: [e.value for e in obj],
)


class User(BaseMixin, db.Model):
    """Represents a Pepto platform user.

    Attributes:
        email: Unique login identifier.
        phone: Phone number (required for 2FA OTP).
        password_hash: Bcrypt-hashed password (never expose in API responses).
        full_name: Display name.
        avatar_url: URL to the user's profile picture.
        role: One of customer / store_owner / delivery_partner / admin.
        is_verified: True once email verification is complete.
        is_phone_verified: True once phone OTP verification is complete.
        two_fa_enabled: True if user has opted into 2FA login.
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
    is_phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    two_fa_enabled: Mapped[bool] = mapped_column(
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

    store: Mapped[Optional["Store"]] = relationship(
        "Store",
        back_populates="owner",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )

    delivery_partner_profile: Mapped[Optional["DeliveryPartner"]] = relationship(
        "DeliveryPartner",
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

    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="customer",
        lazy="select",
        foreign_keys="Order.customer_id",
    )

    # ── Password helpers ──────────────────────────────────────────────────────

    def set_password(self, raw_password: str) -> None:
        """Hash *raw_password* with bcrypt and store it."""
        self.password_hash = bcrypt.generate_password_hash(raw_password).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        """Verify *raw_password* against the stored hash."""
        if not self.password_hash:
            return False
        return bcrypt.check_password_hash(self.password_hash, raw_password)

    # ── Token helpers ─────────────────────────────────────────────────────────

    def generate_verification_token(self) -> str:
        """Generate a signed JWT for email verification (valid 24 h)."""
        import time

        payload = {
            "sub": str(self.id),
            "purpose": "email_verification",
            "iat": int(time.time()),
            "exp": int(time.time()) + 86400,
        }
        secret = current_app.config.get("JWT_SECRET_KEY", "fallback-secret")
        return pyjwt.encode(payload, secret, algorithm="HS256")

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_public_dict(self) -> Dict[str, Any]:
        """Return a safe public representation (no password_hash)."""
        data = self.to_dict(exclude=["password_hash"])
        if isinstance(data.get("role"), UserRole):
            data["role"] = data["role"].value
        return data
