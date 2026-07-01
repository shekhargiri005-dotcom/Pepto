"""
models/product.py — Pet food product listed by a store.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, Enum, Float, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.store import Store
    from app.models.review import Review


class ProductCategory(str, enum.Enum):
    dry_food = "dry_food"
    wet_food = "wet_food"
    treats = "treats"
    supplements = "supplements"
    accessories = "accessories"
    raw_food = "raw_food"
    frozen_food = "frozen_food"


class PetSpecies(str, enum.Enum):
    dog = "dog"
    cat = "cat"
    parrot = "parrot"
    rabbit = "rabbit"
    fish = "fish"
    hamster = "hamster"
    other = "other"


_category_enum = Enum(ProductCategory, name="productcategory", values_callable=lambda o: [e.value for e in o])


class Product(BaseMixin, db.Model):
    """A pet food product listed by a store.

    nutritional_info JSON shape:
        {"protein": 22.5, "fat": 10.0, "fiber": 3.5,
         "moisture": 12.0, "calories_per_100g": 350}

    suitable_for JSON shape:
        {"species": ["dog", "cat"], "age_range": "adult",
         "health_conditions": ["weight_management"]}

    images JSON shape:
        ["https://cdn.example.com/img1.jpg", ...]
    """

    __tablename__ = "products"

    store_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        db.ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    brand: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, index=True)
    category: Mapped[ProductCategory] = mapped_column(
        _category_enum, nullable=False, default=ProductCategory.dry_food
    )
    subcategory: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ingredients: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Nutrition stored as JSONB for flexibility
    nutritional_info: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)

    # Which pets this is suitable for
    suitable_for: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)

    # Pricing
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    # Unit info
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="pack")  # kg/g/pack/can
    weight_grams: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Inventory
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    # Images as JSONB array
    images: Mapped[Optional[List]] = mapped_column(JSONB, nullable=True)

    # Aggregates
    avg_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Relationships ─────────────────────────────────────────────────────────

    store: Mapped["Store"] = relationship("Store", back_populates="products")
    reviews: Mapped[List["Review"]] = relationship(
        "Review", back_populates="product", lazy="dynamic"
    )

    @property
    def effective_price(self) -> float:
        """Return the discounted price if set, otherwise the regular price."""
        return float(self.discount_price) if self.discount_price else float(self.price)
