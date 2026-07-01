"""
models/delivery_tracking.py — Real-time GPS location log for active deliveries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.delivery_partner import DeliveryPartner


class DeliveryTracking(db.Model):
    """Append-only log of GPS pings from a delivery partner during an active delivery.

    One row is written every ~5 seconds via the WebSocket location_update event.
    This table is used to replay the route on the order tracking map and for
    analytics on delivery time vs distance.
    """

    __tablename__ = "delivery_tracking"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    delivery_partner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        db.ForeignKey("delivery_partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[str] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    order: Mapped["Order"] = relationship("Order")
    delivery_partner: Mapped["DeliveryPartner"] = relationship(
        "DeliveryPartner", back_populates="tracking_logs"
    )
