"""
schemas/pet_schemas.py — Pydantic request schemas for pet management endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.pet import PetGender, PetSpecies


class PetCreate(BaseModel):
    """Schema for ``POST /api/pets``."""

    name: str = Field(..., min_length=1, max_length=100, description="Pet's name")
    species: PetSpecies = Field(..., description="Pet species")
    breed: Optional[str] = Field(None, max_length=150, description="Breed (optional)")
    age_years: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Age in years (fractions allowed)"
    )
    weight_kg: Optional[float] = Field(
        None, ge=0.0, le=1000.0, description="Weight in kg"
    )
    gender: PetGender = Field(PetGender.unknown, description="Gender of the pet")
    color: Optional[str] = Field(None, max_length=100, description="Primary colour")
    microchip_id: Optional[str] = Field(
        None, max_length=50, description="ISO 11784 microchip number"
    )
    medical_notes: Optional[str] = Field(
        None, max_length=5000, description="Free-text medical history"
    )
    allergies: Optional[str] = Field(
        None, max_length=2000, description="Known allergens"
    )
    vaccination_status: Optional[Dict[str, Any]] = Field(
        None,
        description='Vaccination records as JSON, e.g. {"rabies": true}',
    )

    @field_validator("age_years")
    @classmethod
    def reasonable_age(cls, value: Optional[float]) -> Optional[float]:
        """Guard against obviously wrong ages."""
        if value is not None and value > 100:
            raise ValueError("Age cannot exceed 100 years.")
        return value


class PetUpdate(BaseModel):
    """Schema for ``PATCH /api/pets/{id}`` — all fields optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    species: Optional[PetSpecies] = None
    breed: Optional[str] = Field(None, max_length=150)
    age_years: Optional[float] = Field(None, ge=0.0, le=100.0)
    weight_kg: Optional[float] = Field(None, ge=0.0, le=1000.0)
    gender: Optional[PetGender] = None
    color: Optional[str] = Field(None, max_length=100)
    microchip_id: Optional[str] = Field(None, max_length=50)
    medical_notes: Optional[str] = Field(None, max_length=5000)
    allergies: Optional[str] = Field(None, max_length=2000)
    vaccination_status: Optional[Dict[str, Any]] = None
    photo_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
