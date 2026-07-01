"""
models/order.py — Customer order and its line items for pet food delivery.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import DateTime, Enum, Float, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.store import Store
    from app.models.delivery_partner import DeliveryPartner
    from app.models.payment import Payment


class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    ready = "ready"
    picked_up = "picked_up"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"
    refunded = "refunded"


class PaymentMethod(str, enum.Enum):
    card = "card"
    upi = "upi"
    netbanking = "netbanking"
    wallet = "wallet"
    cod = "cod"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


_status_enum = Enum(OrderStatus, name="orderstatus", values_callable=lambda o: [e.value for e in o])
_payment_method_enum = Enum(PaymentMethod, name="paymentmethod", values_callable=lambda o: [e.value for e in o])
_payment_status_enum = Enum(PaymentStatus, name="orderpaymentstatus", values_callable=lambda o: [e.value for e in o])


class Order(BaseMixin, db.Model):
    """A customer's food delivery order.

    items JSON shape (snapshot at time of order):
        [{"product_id": "uuid", "product_name": "...", "price": 299.0,
          "quantity": 2, "subtotal": 598.0}, ...]

    delivery_address JSON shape:
        {"line1": "123 MG Road", "city": "Bangalore",
         "state": "Karnataka", "pincode": "560001",
         "lat": 12.97, "lng": 77.59}
    """

    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), db.ForeignKey("users.id"), nullable=False, index=True
    )
    store_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), db.ForeignKey("stores.id"), nullable=False, index=True
    )
    delivery_partner_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), db.ForeignKey("delivery_partners.id"), nullable=True
    )

    status: Mapped[OrderStatus] = mapped_column(
        _status_enum, nullable=False, default=OrderStatus.pending
    )

    # Order contents — snapshot, not FK, so history is preserved if products change
    items: Mapped[List] = mapped_column(JSONB, nullable=False, default=list)

    # Pricing
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    delivery_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    tax: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    platform_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Delivery info
    delivery_address: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    delivery_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivery_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    delivery_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Payment
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(_payment_method_enum, nullable=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        _payment_status_enum, nullable=False, default=PaymentStatus.pending
    )
    razorpay_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    estimated_delivery_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    picked_up_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    customer: Mapped["User"] = relationship("User", back_populates="orders", foreign_keys=[customer_id])
    store: Mapped["Store"] = relationship("Store", back_populates="orders")
    delivery_partner: Mapped[Optional["DeliveryPartner"]] = relationship(
        "DeliveryPartner", back_populates="orders"
    )
    payment: Mapped[Optional["Payment"]] = relationship(
        "Payment", back_populates="order", uselist=False, cascade="all, delete-orphan"
    )
