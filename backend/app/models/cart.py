"""
models/cart.py — Temporary shopping cart items before order placement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.product import Product
    from app.models.store import Store


class CartItem(BaseMixin, db.Model):
    """A single product line in a customer's cart.

    Note: Cart is per-store. If a customer adds items from a second store,
    the existing cart is cleared (same behaviour as Swiggy/Zomato).
    """

    __tablename__ = "cart_items"

    customer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    store_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        db.ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        db.ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # ── Relationships ─────────────────────────────────────────────────────────

    customer: Mapped["User"] = relationship("User")
    product: Mapped["Product"] = relationship("Product")
    store: Mapped["Store"] = relationship("Store")
