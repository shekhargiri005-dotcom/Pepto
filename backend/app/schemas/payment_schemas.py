"""
schemas/payment_schemas.py — Pydantic request schemas for payment endpoints.
"""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, Field


class PaymentIntentCreate(BaseModel):
    """Schema for ``POST /api/payments/create-intent``.

    Initiates a Stripe PaymentIntent for the given booking.
    """

    booking_id: uuid.UUID = Field(
        ..., description="UUID of the confirmed booking to pay for"
    )


class RefundRequest(BaseModel):
    """Schema for ``POST /api/payments/refund``.

    Requests a full or partial refund for a completed payment.
    Only admins or providers (subject to policy) should call this endpoint.
    """

    booking_id: uuid.UUID = Field(
        ..., description="UUID of the booking whose payment should be refunded"
    )
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Human-readable reason for the refund (sent to Stripe metadata)",
    )
