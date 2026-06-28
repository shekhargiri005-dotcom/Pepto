"""
models/availability.py — Availability (weekly schedule) model.

Providers define recurring weekly time windows.  The booking engine uses
these to generate bookable slots on any given date.
"""

from __future__ import annotations

import uuid
from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.provider import ProviderProfile


class Availability(BaseMixin, db.Model):
    """A recurring weekly time block during which a provider accepts bookings.

    Attributes:
        provider_id: FK to the ProviderProfile.
        day_of_week: 0 = Monday … 6 = Sunday (ISO weekday - 1).
        start_time: Block start time (24-hour).
        end_time: Block end time (24-hour).
        slot_duration_minutes: Granularity of bookable slots within the block.
        is_active: Inactive slots are ignored by the booking engine.
    """

    __tablename__ = "availability"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    day_of_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="0=Monday, 1=Tuesday, …, 6=Sunday",
    )
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
        server_default="60",
        comment="Slot size in minutes (e.g. 30, 60, 90)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    provider: Mapped["ProviderProfile"] = relationship(
        "ProviderProfile", back_populates="availability_slots", lazy="select"
    )

    # ── Constraints & indexes ─────────────────────────────────────────────────

    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "day_of_week",
            "start_time",
            name="uq_availability_provider_day_start",
        ),
        Index("ix_availability_provider_day", "provider_id", "day_of_week"),
    )
