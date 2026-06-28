"""
models/review.py — Review model.

One Review is allowed per completed Booking.  Providers may reply publicly.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.user import User
    from app.models.provider import ProviderProfile


class Review(BaseMixin, db.Model):
    """Customer review for a completed service booking.

    Attributes:
        booking_id: FK to the reviewed booking (unique constraint ensures
                    one review per booking).
        reviewer_id: FK to the User (customer) who wrote the review.
        provider_id: FK to the ProviderProfile being reviewed.
        rating: Integer star rating, 1–5 (enforced by DB CHECK constraint).
        comment: Optional written review text.
        photo_urls: JSON list of image URLs attached to the review.
        is_public: If False, the review is hidden from public listings.
        provider_response: Provider's public reply to the review.
        provider_response_at: Timestamp of the provider's reply.
    """

    __tablename__ = "reviews"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo_urls: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    provider_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider_response_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    booking: Mapped["Booking"] = relationship(
        "Booking", back_populates="review", lazy="select"
    )
    reviewer: Mapped["User"] = relationship(
        "User", lazy="select", foreign_keys=[reviewer_id]
    )
    provider: Mapped["ProviderProfile"] = relationship(
        "ProviderProfile",
        back_populates="reviews",
        lazy="select",
        foreign_keys=[provider_id],
    )

    # ── Table-level constraints & indexes ─────────────────────────────────────

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
        Index("ix_reviews_provider_rating", "provider_id", "rating"),
        Index("ix_reviews_provider_created", "provider_id", "created_at"),
    )
