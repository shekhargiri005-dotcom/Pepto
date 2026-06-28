"""
models/provider.py — ProviderProfile model.

Each User with role='provider' has exactly one ProviderProfile that holds
business-specific data including geolocation, ratings, and Stripe Connect info.
"""

from __future__ import annotations

import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.service import Service
    from app.models.booking import Booking
    from app.models.review import Review
    from app.models.availability import Availability


class ProviderProfile(BaseMixin, db.Model):
    """Extended profile for users that offer pet services.

    Attributes:
        user_id: FK to the owning User (unique — one profile per user).
        business_name: Public-facing business name.
        slug: URL-friendly unique identifier (e.g. ``happy-paws-grooming``).
        description: Markdown-compatible business description.
        cover_image_url: Banner/cover image for the listing page.
        avg_rating: Rolling average of all approved reviews (0.00–5.00).
        total_reviews: Cached count of approved reviews.
        total_bookings: Cached count of completed bookings.
        is_available: Whether the provider is currently accepting bookings.
        is_verified_business: Admin-verified business credential flag.
        location: PostGIS geography point (SRID 4326).
        latitude/longitude: Duplicated for fast non-spatial queries.
        stripe_account_id: Stripe Connect Express/Standard account ID.
    """

    __tablename__ = "provider_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # ── Business details ──────────────────────────────────────────────────────

    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(250), unique=True, nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ── Ratings & stats ───────────────────────────────────────────────────────

    avg_rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=Decimal("0.00")
    )
    total_reviews: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_bookings: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # ── Availability flags ────────────────────────────────────────────────────

    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_verified_business: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # ── Geolocation ───────────────────────────────────────────────────────────

    location: Mapped[Optional[object]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Address ───────────────────────────────────────────────────────────────

    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, default="India"
    )
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # ── Stripe Connect ────────────────────────────────────────────────────────

    stripe_account_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    user: Mapped["User"] = relationship(
        "User", back_populates="provider_profile", lazy="select"
    )
    services: Mapped[List["Service"]] = relationship(
        "Service",
        back_populates="provider",
        cascade="all, delete-orphan",
        lazy="select",
    )
    bookings: Mapped[List["Booking"]] = relationship(
        "Booking",
        back_populates="provider_profile",
        lazy="select",
        foreign_keys="Booking.provider_id",
    )
    reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="provider",
        lazy="select",
        foreign_keys="Review.provider_id",
    )
    availability_slots: Mapped[List["Availability"]] = relationship(
        "Availability",
        back_populates="provider",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ── Table-level indexes ───────────────────────────────────────────────────

    __table_args__ = (
        Index("ix_provider_profiles_avg_rating", "avg_rating"),
        Index("ix_provider_profiles_city", "city"),
        # GIST index on location for spatial queries; note: requires PostGIS
        Index(
            "ix_provider_profiles_location",
            "location",
            postgresql_using="gist",
        ),
    )
