"""
models/service.py — Service model.

A Service belongs to a ProviderProfile and represents a single bookable
offering (e.g. "Full Grooming – 90 min – ₹800").
"""

from __future__ import annotations

import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.provider import ProviderProfile
    from app.models.booking import Booking


class ServiceCategory(str, enum.Enum):
    """Categories of pet services available on the platform."""

    grooming = "grooming"
    vet_consultation = "vet_consultation"
    walking = "walking"
    boarding = "boarding"
    training = "training"
    dental = "dental"
    spa = "spa"


_category_enum = Enum(
    ServiceCategory,
    name="servicecategory",
    values_callable=lambda obj: [e.value for e in obj],
)


class Service(BaseMixin, db.Model):
    """A bookable service offered by a provider.

    Attributes:
        provider_id: FK to the owning ProviderProfile.
        name: Short service name visible to customers.
        description: Detailed description.
        price: Price in INR (or configured currency).
        duration: Duration in minutes.
        category: One of the ServiceCategory values.
        is_active: False to hide the service from search results.
        max_concurrent_bookings: How many bookings can overlap at the same slot.
    """

    __tablename__ = "services"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    duration: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Duration of service in minutes"
    )

    category: Mapped[ServiceCategory] = mapped_column(
        _category_enum, nullable=False, index=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )

    max_concurrent_bookings: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Maximum simultaneous bookings allowed for this service slot",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    provider: Mapped["ProviderProfile"] = relationship(
        "ProviderProfile", back_populates="services", lazy="select"
    )
    bookings: Mapped[List["Booking"]] = relationship(
        "Booking", back_populates="service", lazy="select"
    )

    # ── Table-level indexes ───────────────────────────────────────────────────

    __table_args__ = (
        Index("ix_services_provider_category", "provider_id", "category"),
        Index("ix_services_provider_active", "provider_id", "is_active"),
    )
