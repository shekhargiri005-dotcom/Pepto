"""app/api/nutrition.py — Nutritional guide endpoints."""

from flask import Blueprint, request
from app.utils.helpers import success_response, error_response
from app.utils.decorators import require_auth
from app.utils.exceptions import PeptoException
import logging

logger = logging.getLogger(__name__)
nutrition_bp = Blueprint("nutrition_bp", __name__)


@nutrition_bp.route("", methods=["GET"])
def list_guides():
    """GET /api/nutrition — All nutrition guides."""
    from app.services.nutrition_service import NutritionService
    try:
        guides = NutritionService().get_all_guides()
        return success_response(guides)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@nutrition_bp.route("/species", methods=["GET"])
def list_species():
    """GET /api/nutrition/species — Available species list."""
    from app.models.nutrition_guide import GuideSpecies
    return success_response([s.value for s in GuideSpecies])


@nutrition_bp.route("/<string:species>", methods=["GET"])
def get_guides_by_species(species):
    """GET /api/nutrition/:species — All guides for a species (dog/cat/parrot)."""
    from app.services.nutrition_service import NutritionService
    try:
        guides = NutritionService().get_by_species(species)
        return success_response(guides)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@nutrition_bp.route("/<string:species>/<string:category>", methods=["GET"])
def get_guide(species, category):
    """GET /api/nutrition/:species/:category — Specific guide (e.g. dog/puppy)."""
    from app.services.nutrition_service import NutritionService
    try:
        guide = NutritionService().get_guide(species, category)
        return success_response(guide)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@nutrition_bp.route("", methods=["POST"])
@require_auth
def create_guide(current_user):
    """POST /api/nutrition — Create a guide (admin only)."""
    from app.services.nutrition_service import NutritionService
    from app.utils.exceptions import AuthorizationError
    if current_user.role.value != "admin":
        raise AuthorizationError("Admin access required")
    data = request.get_json()
    try:
        guide = NutritionService().create_guide(data)
        return success_response(guide, "Nutrition guide created", 201)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@nutrition_bp.route("/<string:guide_id>", methods=["PUT"])
@require_auth
def update_guide(current_user, guide_id):
    """PUT /api/nutrition/:id — Update a guide (admin only)."""
    from app.services.nutrition_service import NutritionService
    from app.utils.exceptions import AuthorizationError
    if current_user.role.value != "admin":
        raise AuthorizationError("Admin access required")
    data = request.get_json()
    try:
        guide = NutritionService().update_guide(guide_id, data)
        return success_response(guide)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)
