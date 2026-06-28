from flask import Blueprint, request
from app.utils.helpers import success_response, error_response
from app.utils.decorators import require_auth, validate_json
from app.schemas.pet_schemas import PetCreate, PetUpdate
from app.models.pet import Pet
from app.extensions import db
import logging

logger = logging.getLogger(__name__)
pets_bp = Blueprint('pets_bp', __name__)

@pets_bp.route('', methods=['GET'])
@require_auth
def list_pets(current_user):
    try:
        pets = Pet.query.filter_by(customer_id=current_user.id, is_active=True).all()
        return success_response([p.to_dict() for p in pets])
    except Exception as e:
        logger.exception("Error listing pets")
        return error_response("Internal server error", 500)

@pets_bp.route('', methods=['POST'])
@require_auth
@validate_json(PetCreate)
def create_pet(current_user):
    try:
        data = request.json
        pet = Pet(customer_id=current_user.id, **data)
        db.session.add(pet)
        db.session.commit()
        return success_response(pet.to_dict(), "Pet created successfully", 201)
    except Exception as e:
        db.session.rollback()
        logger.exception("Error creating pet")
        return error_response("Internal server error", 500)

@pets_bp.route('/<uuid:pet_id>', methods=['PUT'])
@require_auth
@validate_json(PetUpdate)
def update_pet(current_user, pet_id):
    try:
        pet = db.session.get(Pet, pet_id)
        if not pet or pet.customer_id != current_user.id:
            return error_response("Pet not found", 404)
            
        data = request.json
        for key, value in data.items():
            setattr(pet, key, value)
            
        db.session.commit()
        return success_response(pet.to_dict(), "Pet updated successfully")
    except Exception as e:
        db.session.rollback()
        logger.exception("Error updating pet")
        return error_response("Internal server error", 500)

@pets_bp.route('/<uuid:pet_id>', methods=['DELETE'])
@require_auth
def delete_pet(current_user, pet_id):
    try:
        pet = db.session.get(Pet, pet_id)
        if not pet or pet.customer_id != current_user.id:
            return error_response("Pet not found", 404)
            
        pet.is_active = False
        pet.soft_delete()
        db.session.commit()
        return success_response(None, "Pet deleted successfully")
    except Exception as e:
        db.session.rollback()
        logger.exception("Error deleting pet")
        return error_response("Internal server error", 500)
