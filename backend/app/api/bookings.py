from flask import Blueprint, request
from app.utils.helpers import success_response, error_response
from app.utils.decorators import require_auth, validate_json, provider_required
from app.schemas.booking_schemas import BookingCreate, BookingStatusUpdate, CancellationRequest
from app.services.booking_service import BookingService
from app.utils.exceptions import PeptoException
import logging

logger = logging.getLogger(__name__)
bookings_bp = Blueprint('bookings_bp', __name__)
booking_service = BookingService()

@bookings_bp.route('', methods=['POST'])
@require_auth
@validate_json(BookingCreate)
def create_booking(current_user):
    try:
        data = request.json
        booking = booking_service.create_booking(current_user.id, data)
        return success_response(booking.to_dict(), "Booking created successfully", 201)
    except PeptoException as e:
        return error_response(e.message, e.status_code, e.error_code)
    except Exception as e:
        logger.exception("Error creating booking")
        return error_response("Internal server error", 500)

@bookings_bp.route('', methods=['GET'])
@require_auth
def list_bookings(current_user):
    try:
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        
        if current_user.role.name == 'provider':
            provider_id = current_user.provider_profile.id
            date = request.args.get('date')
            result = booking_service.get_provider_bookings(provider_id, status, date, page)
        else:
            result = booking_service.get_customer_bookings(current_user.id, status, page)
            
        return success_response(result)
    except Exception as e:
        logger.exception("Error listing bookings")
        return error_response("Internal server error", 500)

@bookings_bp.route('/<uuid:booking_id>', methods=['GET'])
@require_auth
def get_booking(current_user, booking_id):
    try:
        from app.models.booking import Booking
        from app.extensions import db
        booking = db.session.get(Booking, booking_id)
        if not booking:
            return error_response("Booking not found", 404)
            
        if current_user.role.name == 'customer' and booking.customer_id != current_user.id:
            return error_response("Unauthorized", 403)
        if current_user.role.name == 'provider' and booking.provider_id != current_user.provider_profile.id:
            return error_response("Unauthorized", 403)
            
        return success_response(booking.to_dict())
    except Exception as e:
        logger.exception("Error getting booking")
        return error_response("Internal server error", 500)

@bookings_bp.route('/<uuid:booking_id>/status', methods=['PUT'])
@require_auth
@provider_required
@validate_json(BookingStatusUpdate)
def update_status(current_user, booking_id):
    try:
        data = request.json
        booking = booking_service.update_booking_status(
            booking_id=booking_id,
            new_status=data['status'],
            actor_id=current_user.id,
            reason=data.get('reason')
        )
        return success_response(booking.to_dict(), "Status updated successfully")
    except PeptoException as e:
        return error_response(e.message, e.status_code, e.error_code)
    except Exception as e:
        logger.exception("Error updating status")
        return error_response("Internal server error", 500)

@bookings_bp.route('/<uuid:booking_id>/cancel', methods=['POST'])
@require_auth
@validate_json(CancellationRequest)
def cancel_booking(current_user, booking_id):
    try:
        data = request.json
        booking = booking_service.cancel_booking(
            booking_id=booking_id,
            user_id=current_user.id,
            reason=data['reason']
        )
        return success_response(booking.to_dict(), "Booking cancelled successfully")
    except PeptoException as e:
        return error_response(e.message, e.status_code, e.error_code)
    except Exception as e:
        logger.exception("Error cancelling booking")
        return error_response("Internal server error", 500)

@bookings_bp.route('/availability-check', methods=['GET'])
@require_auth
def check_availability(current_user):
    try:
        provider_id = request.args.get('provider_id')
        service_id = request.args.get('service_id')
        date = request.args.get('date')
        start_time = request.args.get('start_time')
        
        if not all([provider_id, service_id, date, start_time]):
            return error_response("Missing parameters", 400)
            
        is_available = booking_service.check_availability(provider_id, service_id, date, start_time)
        return success_response({"available": is_available})
    except PeptoException as e:
        return error_response(e.message, e.status_code, e.error_code)
    except Exception as e:
        logger.exception("Error checking availability")
        return error_response("Internal server error", 500)
