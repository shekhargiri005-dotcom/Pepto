"""
services/nutrition_service.py — CRUD for nutritional guides.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.extensions import db
from app.models.nutrition_guide import NutritionGuide, GuideSpecies, GuideCategory
from app.utils.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class NutritionService:

    def get_all_guides(self) -> List[Dict]:
        guides = NutritionGuide.query.order_by(NutritionGuide.species, NutritionGuide.category).all()
        return [g.to_dict() for g in guides]

    def get_by_species(self, species: str) -> List[Dict]:
        try:
            species_enum = GuideSpecies(species)
        except ValueError:
            raise ValidationError(f"Invalid species '{species}'. Valid: dog, cat, parrot")
        guides = NutritionGuide.query.filter_by(species=species_enum).order_by(NutritionGuide.category).all()
        return [g.to_dict() for g in guides]

    def get_guide(self, species: str, category: str) -> Dict:
        try:
            species_enum = GuideSpecies(species)
            category_enum = GuideCategory(category)
        except ValueError as e:
            raise ValidationError(str(e))
        guide = NutritionGuide.query.filter_by(species=species_enum, category=category_enum).first()
        if not guide:
            raise NotFoundError(f"No guide found for {species}/{category}")
        return guide.to_dict()

    def create_guide(self, data: dict) -> Dict:
        try:
            guide = NutritionGuide(**data)
            db.session.add(guide)
            db.session.commit()
            return guide.to_dict()
        except Exception as exc:
            db.session.rollback()
            raise ValidationError(str(exc))

    def update_guide(self, guide_id: str, data: dict) -> Dict:
        guide = NutritionGuide.query.get(guide_id)
        if not guide:
            raise NotFoundError("Guide not found")
        for key, value in data.items():
            if hasattr(guide, key):
                setattr(guide, key, value)
        db.session.commit()
        return guide.to_dict()
