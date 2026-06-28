from flask import Blueprint, request
from app.utils.helpers import success_response, error_response
from app.utils.decorators import require_auth, validate_json, provider_required
from app.schemas.payment_schemas import PaymentIntentCreate, RefundRequest
from app.services.payment_service import PaymentService
from app.utils.exceptions import PeptoException
import logging

logger = logging.getLogger(__name__)
payments_bp = Blueprint('payments_bp', __name__)
payment_service = PaymentService()

@payments_bp.route('/intent', methods=['POST'])
@require_auth
@validate_json(PaymentIntentCreate)
def create_intent(current_user):
    try:
        data = request.json
        result = payment_service.create_payment_intent(data['booking_id'], current_user.id)
        return success_response(result, "Payment intent created", 201)
    except PeptoException as e:
        return error_response(e.message, e.status_code, e.error_code)
    except Exception as e:
        logger.exception("Error creating payment intent")
        return error_response("Internal server error", 500)

@payments_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    try:
        payload = request.get_data(as_text=True)
        sig_header = request.headers.get('Stripe-Signature')
        if not sig_header:
            return error_response("Missing signature", 400)
            
        payment_service.handle_webhook(payload, sig_header)
        return success_response({"status": "success"})
    except PeptoException as e:
        return error_response(e.message, e.status_code, e.error_code)
    except Exception as e:
        logger.exception("Webhook error")
        return error_response("Internal server error", 500)

@payments_bp.route('/refund', methods=['POST'])
@require_auth
@validate_json(RefundRequest)
def request_refund(current_user):
    try:
        data = request.json
        result = payment_service.create_refund(data['booking_id'], current_user.id)
        return success_response(result, "Refund processed")
    except PeptoException as e:
        return error_response(e.message, e.status_code, e.error_code)
    except Exception as e:
        logger.exception("Error processing refund")
        return error_response("Internal server error", 500)

@payments_bp.route('/earnings', methods=['GET'])
@require_auth
@provider_required
def provider_earnings(current_user):
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        result = payment_service.get_provider_earnings(
            current_user.provider_profile.id, start_date, end_date
        )
        return success_response(result)
    except Exception as e:
        logger.exception("Error fetching earnings")
        return error_response("Internal server error", 500)
