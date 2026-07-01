"""
models/store.py — Pet food store owned by a store_owner user.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, Float, Integer, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography

from app.extensions import db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.product import Product
    from app.models.order import Order
    from app.models.review import Review


class Store(BaseMixin, db.Model):
    """A pet food store listed on the Pepto marketplace.

    Attributes:
        owner_id: FK to the store_owner User.
        name: Display name of the store.
        slug: URL-friendly unique identifier.
        description: Short description shown on listing.
        logo_url: Square logo image URL.
        cover_image_url: Banner image URL.
        address: Full street address string.
        city: City name for display and filtering.
        state: State / region.
        lat / lng: Coordinates for geospatial queries.
        phone / email: Customer-facing contact details.
        open_time / close_time: Daily opening hours.
        delivery_radius_km: How far the store delivers.
        min_order_amount: Minimum basket value (INR) to place an order.
        delivery_charge: Flat delivery fee (INR).
        avg_delivery_minutes: Typical delivery ETA shown to customers.
        is_verified: Set by admin after vetting the store.
        is_open: Store owner can toggle this throughout the day.
        avg_rating: Denormalised average from Review rows.
        total_orders: Counter incremented per delivered order.
        razorpay_account_id: For split payments to the store.
    """

    __tablename__ = "stores"

    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Address
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location: Mapped[Optional[Any]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )

    # Contact
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Hours
    open_time: Mapped[Optional[Any]] = mapped_column(Time, nullable=True)
    close_time: Mapped[Optional[Any]] = mapped_column(Time, nullable=True)

    # Delivery settings
    delivery_radius_km: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    min_order_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    delivery_charge: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    avg_delivery_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    # Status
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    # Aggregates (denormalised for performance)
    avg_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Payment
    razorpay_account_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    owner: Mapped["User"] = relationship("User", back_populates="store")
    products: Mapped[List["Product"]] = relationship(
        "Product", back_populates="store", cascade="all, delete-orphan", lazy="dynamic"
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order", back_populates="store", lazy="dynamic"
    )
    reviews: Mapped[List["Review"]] = relationship(
        "Review", back_populates="store", lazy="dynamic"
    )

    def to_dict(self, **kwargs) -> Dict[str, Any]:
        d = super().to_dict(**kwargs)
        d.pop("location", None)  # geography type — not JSON serialisable
        return d
