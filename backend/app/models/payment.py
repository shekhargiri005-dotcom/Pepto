"""
models/payment.py — Payment model.

Tracks the Stripe PaymentIntent lifecycle for each Booking.
Supports full and partial refunds.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.booking import Booking


class PaymentStatus(str, enum.Enum):
    """States of a Stripe payment lifecycle."""

    pending = "pending"
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"
    refunded = "refunded"
    partially_refunded = "partially_refunded"


_payment_status_enum = Enum(
    PaymentStatus,
    name="paymentstatus",
    values_callable=lambda obj: [e.value for e in obj],
)


class Payment(BaseMixin, db.Model):
    """Records the payment for a single booking.

    Attributes:
        booking_id: FK to the associated Booking (unique: 1 payment per booking).
        amount: Gross amount charged to the customer.
        platform_fee: Pepto's fee deducted from the charge.
        provider_earning: Net amount due to the provider.
        currency: ISO 4217 currency code (default INR).
        payment_intent_id: Stripe PaymentIntent ID (pi_...).
        payment_method_id: Stripe PaymentMethod ID (pm_...).
        payment_method_type: e.g. 'card', 'upi', 'netbanking'.
        status: Current payment status.
        refund_id: Stripe Refund object ID (re_...).
        refund_amount: Amount actually refunded.
        refunded_at: Timestamp of the refund.
        metadata: Arbitrary JSON blob for extra Stripe metadata.
    """

    __tablename__ = "payments"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # ── Financial ─────────────────────────────────────────────────────────────

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    platform_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    provider_earning: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="INR", server_default="INR"
    )

    # ── Stripe IDs ────────────────────────────────────────────────────────────

    payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
    )
    payment_method_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    payment_method_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )

    # ── Status ────────────────────────────────────────────────────────────────

    status: Mapped[PaymentStatus] = mapped_column(
        _payment_status_enum,
        nullable=False,
        default=PaymentStatus.pending,
        index=True,
    )

    # ── Refunds ───────────────────────────────────────────────────────────────

    refund_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    refund_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    refunded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Extra data ────────────────────────────────────────────────────────────

    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    booking: Mapped["Booking"] = relationship(
        "Booking", back_populates="payment", lazy="select"
    )

    __table_args__ = (
        Index("ix_payments_status", "status"),
        Index("ix_payments_booking_status", "booking_id", "status"),
    )
