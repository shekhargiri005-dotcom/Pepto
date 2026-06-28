"""
models/booking.py — Booking model.

A Booking connects a customer to a provider's service for a specific
date/time slot, optionally for a registered pet.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.provider import ProviderProfile
    from app.models.service import Service
    from app.models.pet import Pet
    from app.models.payment import Payment
    from app.models.review import Review


class BookingStatus(str, enum.Enum):
    """Lifecycle states of a booking."""

    pending = "pending"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    refunded = "refunded"


_status_enum = Enum(
    BookingStatus,
    name="bookingstatus",
    values_callable=lambda obj: [e.value for e in obj],
)


class Booking(BaseMixin, db.Model):
    """Represents a confirmed or pending appointment.

    Financial fields (total_amount, platform_fee, provider_earning) are
    populated when the booking is created based on the service price and
    the platform fee percentage configured in settings.

    Attributes:
        customer_id: FK to users (role=customer).
        provider_id: FK to users (role=provider) — denormalised for quick queries.
        service_id: FK to the booked service.
        pet_id: FK to the pet being serviced (optional).
        booking_date: Calendar date of the appointment.
        start_time: Appointment start time.
        end_time: Auto-calculated end time (start + service.duration).
        status: Current lifecycle status.
        total_amount: Full amount charged to the customer.
        platform_fee: Pepto's cut.
        provider_earning: Amount transferred to the provider.
        notes: Customer-supplied free-text notes for the provider.
        cancellation_reason: Reason text when status=cancelled.
        cancelled_at: Timestamp of cancellation.
    """

    __tablename__ = "bookings"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    pet_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Schedule ──────────────────────────────────────────────────────────────

    booking_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    # ── Status ────────────────────────────────────────────────────────────────

    status: Mapped[BookingStatus] = mapped_column(
        _status_enum,
        nullable=False,
        default=BookingStatus.pending,
        index=True,
    )

    # ── Financial ─────────────────────────────────────────────────────────────

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    platform_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    provider_earning: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )

    # ── Notes & cancellation ──────────────────────────────────────────────────

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    customer: Mapped["User"] = relationship(
        "User",
        back_populates="bookings_as_customer",
        lazy="select",
        foreign_keys=[customer_id],
    )
    provider_profile: Mapped["ProviderProfile"] = relationship(
        "ProviderProfile",
        back_populates="bookings",
        lazy="select",
        foreign_keys=[provider_id],
    )
    service: Mapped["Service"] = relationship(
        "Service", back_populates="bookings", lazy="select"
    )
    pet: Mapped[Optional["Pet"]] = relationship(
        "Pet", back_populates="bookings", lazy="select"
    )
    payment: Mapped[Optional["Payment"]] = relationship(
        "Payment",
        back_populates="booking",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )
    review: Mapped[Optional["Review"]] = relationship(
        "Review",
        back_populates="booking",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ── Table-level indexes ───────────────────────────────────────────────────

    __table_args__ = (
        Index("ix_bookings_customer_date", "customer_id", "booking_date"),
        Index("ix_bookings_provider_date", "provider_id", "booking_date"),
        Index("ix_bookings_status_date", "status", "booking_date"),
    )
