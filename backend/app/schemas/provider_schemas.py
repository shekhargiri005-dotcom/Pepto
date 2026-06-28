"""
schemas/provider_schemas.py — Pydantic schemas for provider, service,
availability and search endpoints.
"""

from __future__ import annotations

import re
from datetime import time
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.service import ServiceCategory


# ── Provider profile ──────────────────────────────────────────────────────────


class ProviderProfileCreate(BaseModel):
    """Schema for creating a new provider profile (``POST /api/providers/profile``)."""

    business_name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: str = Field("India", max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    category: Optional[ServiceCategory] = Field(
        None, description="Primary service category"
    )

    @model_validator(mode="after")
    def lat_lng_together(self) -> "ProviderProfileCreate":
        """Latitude and longitude must be provided together or not at all."""
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError(
                "Both latitude and longitude must be provided together."
            )
        return self


class ProviderProfileUpdate(BaseModel):
    """Schema for partial provider profile update (``PATCH /api/providers/profile``)."""

    business_name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    is_available: Optional[bool] = None

    @model_validator(mode="after")
    def lat_lng_together(self) -> "ProviderProfileUpdate":
        """Both coordinates must be supplied together if either is given."""
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError(
                "Both latitude and longitude must be provided together."
            )
        return self


# ── Services ──────────────────────────────────────────────────────────────────


class ServiceCreate(BaseModel):
    """Schema for creating a service under a provider profile."""

    name: str = Field(..., min_length=2, max_length=200)
    description: str = Field("", max_length=3000)
    price: Decimal = Field(..., gt=Decimal("0"), description="Price in INR, must be > 0")
    duration: int = Field(
        ..., gt=0, le=480, description="Duration in minutes (1–480)"
    )
    category: ServiceCategory
    max_concurrent_bookings: int = Field(1, ge=1, le=50)


class ServiceUpdate(BaseModel):
    """Schema for partially updating an existing service."""

    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=3000)
    price: Optional[Decimal] = Field(None, gt=Decimal("0"))
    duration: Optional[int] = Field(None, gt=0, le=480)
    category: Optional[ServiceCategory] = None
    is_active: Optional[bool] = None
    max_concurrent_bookings: Optional[int] = Field(None, ge=1, le=50)


# ── Search ────────────────────────────────────────────────────────────────────


class SearchQuery(BaseModel):
    """Query parameters for the provider search endpoint."""

    lat: float = Field(..., ge=-90.0, le=90.0, description="Searcher's latitude")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Searcher's longitude")
    radius_km: float = Field(
        10.0, gt=0, le=500.0, description="Search radius in kilometres"
    )
    category: Optional[ServiceCategory] = Field(
        None, description="Filter by service category"
    )
    min_rating: Optional[float] = Field(
        None, ge=1.0, le=5.0, description="Minimum average rating (1–5)"
    )
    min_price: Optional[Decimal] = Field(
        None, ge=Decimal("0"), description="Minimum service price"
    )
    max_price: Optional[Decimal] = Field(
        None, ge=Decimal("0"), description="Maximum service price"
    )
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)

    @model_validator(mode="after")
    def price_range_valid(self) -> "SearchQuery":
        """Ensure min_price ≤ max_price when both are supplied."""
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price must be less than or equal to max_price.")
        return self


# ── Availability ──────────────────────────────────────────────────────────────


class AvailabilityCreate(BaseModel):
    """Schema for creating a weekly availability slot."""

    day_of_week: int = Field(
        ..., ge=0, le=6, description="0=Monday … 6=Sunday"
    )
    start_time: time = Field(..., description="Slot start time (HH:MM)")
    end_time: time = Field(..., description="Slot end time (HH:MM)")
    slot_duration_minutes: int = Field(
        60, ge=15, le=480, description="Granularity of bookable slots (minutes)"
    )

    @model_validator(mode="after")
    def end_after_start(self) -> "AvailabilityCreate":
        """End time must be strictly after start time."""
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")
        return self
