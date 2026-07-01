"""
models/__init__.py — Import all models so Alembic autogenerate can detect them.

Every model class must be imported here; otherwise Flask-Migrate will not
pick up the tables for `flask db migrate` autogeneration.
"""

from app.models.cart import CartItem  # noqa: F401
from app.models.delivery_partner import DeliveryPartner  # noqa: F401
from app.models.delivery_tracking import DeliveryTracking  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.nutrition_guide import NutritionGuide  # noqa: F401
from app.models.order import Order  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.pet import Pet  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.review import Review  # noqa: F401
from app.models.store import Store  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = [
    "User",
    "Store",
    "Product",
    "Order",
    "Payment",
    "Pet",
    "DeliveryPartner",
    "DeliveryTracking",
    "CartItem",
    "NutritionGuide",
    "Review",
    "Notification",
]
