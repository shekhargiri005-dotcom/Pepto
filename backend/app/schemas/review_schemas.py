"""
schemas/review_schemas.py — Pydantic request schemas for review endpoints.
"""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ReviewCreate(BaseModel):
    """Schema for ``POST /api/reviews``.

    A review is tied to a specific completed booking.
    """

    booking_id: uuid.UUID = Field(
        ..., description="UUID of the completed booking being reviewed"
    )
    rating: int = Field(
        ..., ge=1, le=5, description="Star rating between 1 (worst) and 5 (best)"
    )
    comment: Optional[str] = Field(
        None, max_length=2000, description="Optional written review text"
    )

    @field_validator("rating")
    @classmethod
    def rating_in_range(cls, value: int) -> int:
        """Redundant guard — pydantic ge/le handles this, but explicit is better."""
        if not (1 <= value <= 5):
            raise ValueError("Rating must be between 1 and 5.")
        return value


class ProviderResponseSchema(BaseModel):
    """Schema for ``POST /api/reviews/{id}/response`` (provider only).

    Allows a provider to post a public reply to a customer review.
    """

    response: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Provider's public reply to the review",
    )
