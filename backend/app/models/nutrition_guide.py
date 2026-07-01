"""
models/nutrition_guide.py — Nutritional infographic content for dogs, cats, and parrots.
"""

from __future__ import annotations

import enum
from typing import List, Optional

from sqlalchemy import Enum, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.base import BaseMixin


class GuideSpecies(str, enum.Enum):
    dog = "dog"
    cat = "cat"
    parrot = "parrot"


class GuideCategory(str, enum.Enum):
    # Dog categories
    puppy = "puppy"
    adult = "adult"
    senior = "senior"
    # Cat categories
    kitten = "kitten"
    # cat adult / senior shared with dog
    # Parrot categories
    budgerigar = "budgerigar"       # small parrots
    african_grey = "african_grey"   # medium parrots
    macaw = "macaw"                 # large parrots


_species_enum = Enum(GuideSpecies, name="guidespecies", values_callable=lambda o: [e.value for e in o])
_category_enum = Enum(GuideCategory, name="guidecategory", values_callable=lambda o: [e.value for e in o])


class NutritionGuide(BaseMixin, db.Model):
    """Visual nutritional guide for a pet species + age/size category.

    recommended_foods JSON shape:  ["High-quality kibble", "Wet food", ...]
    forbidden_foods JSON shape:    [{"food": "Chocolate", "reason": "Toxic theobromine"}, ...]
    health_notes JSON shape:       ["DHA for brain development", "Calcium-phosphorus balance", ...]

    display_config JSON shape:
        {"primary_color": "#FF6B35", "icon": "dog-puppy",
         "accent_color": "#FFF3E0"}
    """

    __tablename__ = "nutrition_guides"

    species: Mapped[GuideSpecies] = mapped_column(_species_enum, nullable=False, index=True)
    category: Mapped[GuideCategory] = mapped_column(_category_enum, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Macronutrient ranges (%)
    protein_min: Mapped[float] = mapped_column(Float, nullable=False)
    protein_max: Mapped[float] = mapped_column(Float, nullable=False)
    fat_min: Mapped[float] = mapped_column(Float, nullable=False)
    fat_max: Mapped[float] = mapped_column(Float, nullable=False)
    fiber_min: Mapped[float] = mapped_column(Float, nullable=False)
    fiber_max: Mapped[float] = mapped_column(Float, nullable=False)
    moisture_min: Mapped[float] = mapped_column(Float, nullable=False)
    moisture_max: Mapped[float] = mapped_column(Float, nullable=False)

    # Caloric needs
    calories_min_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    calories_max_per_day: Mapped[int] = mapped_column(Integer, nullable=False)

    # Feeding guidelines
    meals_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    serving_size_description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    water_needs: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Food lists stored as JSONB
    recommended_foods: Mapped[Optional[List]] = mapped_column(JSONB, nullable=True)
    forbidden_foods: Mapped[Optional[List]] = mapped_column(JSONB, nullable=True)
    health_notes: Mapped[Optional[List]] = mapped_column(JSONB, nullable=True)

    # Visual display configuration
    display_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
