"""
models/pet.py — Pet model.

Customers register their pets so that providers can see medical/dietary
information at booking time.
"""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.booking import Booking


class PetSpecies(str, enum.Enum):
    """Supported pet species."""

    dog = "dog"
    cat = "cat"
    bird = "bird"
    rabbit = "rabbit"
    fish = "fish"
    hamster = "hamster"
    other = "other"


class PetGender(str, enum.Enum):
    """Pet gender."""

    male = "male"
    female = "female"
    unknown = "unknown"


_species_enum = Enum(
    PetSpecies,
    name="petspecies",
    values_callable=lambda obj: [e.value for e in obj],
)
_gender_enum = Enum(
    PetGender,
    name="petgender",
    values_callable=lambda obj: [e.value for e in obj],
)


class Pet(BaseMixin, db.Model):
    """A pet owned by a customer.

    Attributes:
        customer_id: FK to the owning User (role=customer).
        name: Pet's display name.
        species: Broad species classification.
        breed: Specific breed (optional).
        age_years: Age in years (can be fractional, e.g. 0.5 for 6 months).
        weight_kg: Weight in kilograms.
        gender: male / female / unknown.
        color: Primary coat/feather/scale color.
        microchip_id: ISO 11784 microchip number.
        medical_notes: Free-text medical history notes.
        allergies: Known allergens.
        vaccination_status: JSON dict, e.g. {"rabies": true, "parvo": "2024-01-10"}.
        photo_url: Profile photo URL.
        is_active: False for deleted / archived pets.
    """

    __tablename__ = "pets"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[PetSpecies] = mapped_column(_species_enum, nullable=False)
    breed: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    age_years: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gender: Mapped[PetGender] = mapped_column(
        _gender_enum, nullable=False, default=PetGender.unknown
    )
    color: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    microchip_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, unique=True
    )
    medical_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    allergies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vaccination_status: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    customer: Mapped["User"] = relationship(
        "User",
        back_populates="pets",
        lazy="select",
        foreign_keys=[customer_id],
    )
    bookings: Mapped[List["Booking"]] = relationship(
        "Booking", back_populates="pet", lazy="select"
    )

    __table_args__ = (
        Index("ix_pets_customer_species", "customer_id", "species"),
    )
