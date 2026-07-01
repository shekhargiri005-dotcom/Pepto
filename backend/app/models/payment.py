"""
models/payment.py — Payment record for a Pepto order (Razorpay).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.order import Order


class Payment(BaseMixin, db.Model):
    """Razorpay payment record linked to an order.

    Attributes:
        order_id: FK to the Order this payment settles.
        amount: Total amount charged (INR paise stored, displayed in ₹).
        currency: Always 'INR' for this platform.
        razorpay_order_id: Razorpay's order ID (rzp_order_*).
        razorpay_payment_id: Razorpay's payment ID after capture (pay_*).
        razorpay_signature: Webhook signature for verification.
        method: card / upi / netbanking / wallet / cod.
        status: pending / captured / failed / refunded.
        platform_fee: Amount retained by Pepto (INR).
        store_earning: Amount transferred to store (INR).
        refunded_amount: Amount refunded if applicable (INR).
        refund_id: Razorpay refund ID if a refund was issued.
        paid_at: Timestamp of successful capture.
        refunded_at: Timestamp of refund.
    """

    __tablename__ = "payments"

    order_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        db.ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    # Razorpay IDs
    razorpay_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    razorpay_signature: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # Split
    platform_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    store_earning: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)

    # Refund
    refunded_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    refund_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    order: Mapped["Order"] = relationship("Order", back_populates="payment")
