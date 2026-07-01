"""
models/delivery_partner.py — Delivery partner profile linked to a delivery_partner user.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Float, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.order import Order
    from app.models.delivery_tracking import DeliveryTracking


class DeliveryPartner(BaseMixin, db.Model):
    """Profile for a delivery partner user.

    Attributes:
        user_id: FK to the delivery_partner User.
        vehicle_type: bicycle | motorcycle | car
        vehicle_number: Plate number for identification.
        current_lat / current_lng: Live GPS position (updated via WebSocket).
        is_online: Partner is available to receive assignments.
        is_available: Partner has no active delivery (derived state).
        current_order_id: FK to the order they are currently delivering.
        avg_rating: Average customer rating for deliveries.
        total_deliveries: Total completed deliveries.
        avg_delivery_minutes: Their personal average delivery time.
        total_earnings: Cumulative earnings in INR.
    """

    __tablename__ = "delivery_partners"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Vehicle
    vehicle_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True  # bicycle | motorcycle | car
    )
    vehicle_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Live location — updated every ~5 s when on delivery
    current_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Availability
    is_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    current_order_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), db.ForeignKey("orders.id", use_alter=True), nullable=True
    )

    # Stats
    avg_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_deliveries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_delivery_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    total_earnings: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)

    # ── Relationships ─────────────────────────────────────────────────────────

    user: Mapped["User"] = relationship("User", back_populates="delivery_partner_profile")
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="delivery_partner",
        foreign_keys="Order.delivery_partner_id",
        lazy="dynamic",
    )
    tracking_logs: Mapped[List["DeliveryTracking"]] = relationship(
        "DeliveryTracking", back_populates="delivery_partner", lazy="dynamic"
    )
