"""
schemas/booking_schemas.py — Pydantic request schemas for booking endpoints.
"""

from __future__ import annotations

import uuid
from datetime import date, time
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.booking import BookingStatus


class BookingCreate(BaseModel):
    """Schema for ``POST /api/bookings``."""

    provider_id: uuid.UUID = Field(..., description="UUID of the provider profile")
    service_id: uuid.UUID = Field(..., description="UUID of the service to book")
    pet_id: Optional[uuid.UUID] = Field(
        None, description="UUID of the pet (optional)"
    )
    booking_date: date = Field(..., description="Appointment date (YYYY-MM-DD)")
    start_time: time = Field(..., description="Appointment start time (HH:MM)")
    notes: Optional[str] = Field(
        None, max_length=1000, description="Free-text notes for the provider"
    )

    @field_validator("booking_date")
    @classmethod
    def date_not_in_past(cls, value: date) -> date:
        """Ensure booking date is today or in the future."""
        from datetime import date as _date

        if value < _date.today():
            raise ValueError("Booking date cannot be in the past.")
        return value


class BookingStatusUpdate(BaseModel):
    """Schema for ``PATCH /api/bookings/{id}/status`` (provider/admin only)."""

    status: BookingStatus = Field(..., description="New booking status")
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional reason (required when cancelling)",
    )

    @field_validator("status")
    @classmethod
    def status_is_valid(cls, value: BookingStatus) -> BookingStatus:
        """Admin/provider can only set certain statuses via this endpoint."""
        allowed = {
            BookingStatus.confirmed,
            BookingStatus.in_progress,
            BookingStatus.completed,
            BookingStatus.cancelled,
        }
        if value not in allowed:
            raise ValueError(
                f"Status must be one of: {', '.join(s.value for s in allowed)}."
            )
        return value


class CancellationRequest(BaseModel):
    """Schema for ``POST /api/bookings/{id}/cancel`` (customer)."""

    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional cancellation reason",
    )
