"""
models/__init__.py — Import all models so Alembic autogenerate can detect them.

Every model class must be imported here; otherwise Flask-Migrate will not
pick up the tables for ``flask db migrate`` autogeneration.
"""

from app.models.availability import Availability  # noqa: F401
from app.models.booking import Booking  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.pet import Pet  # noqa: F401
from app.models.provider import ProviderProfile  # noqa: F401
from app.models.review import Review  # noqa: F401
from app.models.service import Service  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = [
    "User",
    "ProviderProfile",
    "Service",
    "Pet",
    "Booking",
    "Review",
    "Payment",
    "Availability",
]
