"""app/api/payments.py — Razorpay payment endpoints."""

import hashlib
import hmac
import logging

from flask import Blueprint, current_app, request

from app.utils.helpers import success_response, error_response
from app.utils.decorators import require_auth
from app.utils.exceptions import PeptoException

logger = logging.getLogger(__name__)
payments_bp = Blueprint("payments_bp", __name__)


@payments_bp.route("/create-order", methods=["POST"])
@require_auth
def create_razorpay_order(current_user):
    """POST /api/payments/create-order — Create a Razorpay order for checkout.

    Body: {"order_id": "<pepto_order_uuid>"}
    Returns: {razorpay_order_id, amount, currency, key_id}
    """
    from app.services.payment_service import PaymentService
    data = request.get_json() or {}
    order_id = data.get("order_id")
    if not order_id:
        return error_response("order_id is required", 400)
    try:
        result = PaymentService().create_razorpay_order(current_user.id, order_id)
        return success_response(result)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@payments_bp.route("/verify", methods=["POST"])
@require_auth
def verify_payment(current_user):
    """POST /api/payments/verify — Verify Razorpay signature after successful payment.

    Body: {
        "razorpay_order_id": "order_xxx",
        "razorpay_payment_id": "pay_xxx",
        "razorpay_signature": "sha256_hmac"
    }
    """
    from app.services.payment_service import PaymentService
    data = request.get_json() or {}
    required = ["razorpay_order_id", "razorpay_payment_id", "razorpay_signature"]
    if not all(data.get(k) for k in required):
        return error_response("razorpay_order_id, razorpay_payment_id, and razorpay_signature are required", 400)
    try:
        result = PaymentService().verify_payment(current_user.id, data)
        return success_response(result, "Payment verified successfully")
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@payments_bp.route("/webhook", methods=["POST"])
def razorpay_webhook():
    """POST /api/payments/webhook — Razorpay webhook handler (no auth — verified by signature)."""
    from app.services.payment_service import PaymentService

    payload = request.get_data(as_text=True)
    webhook_secret = current_app.config.get("RAZORPAY_WEBHOOK_SECRET", "")

    # Verify webhook signature
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    received = request.headers.get("X-Razorpay-Signature", "")
    if not hmac.compare_digest(expected, received):
        logger.warning("Razorpay webhook signature mismatch")
        return error_response("Invalid signature", 400)

    event = request.get_json()
    event_type = event.get("event", "")
    try:
        PaymentService().handle_webhook(event_type, event)
        return success_response(None, "Webhook processed")
    except Exception as exc:
        logger.exception("Webhook processing error: %s", exc)
        return error_response("Webhook processing failed", 500)


@payments_bp.route("/refund", methods=["POST"])
@require_auth
def refund_payment(current_user):
    """POST /api/payments/refund — Issue a refund for a cancelled order.

    Body: {"order_id": "<uuid>"}
    """
    from app.services.payment_service import PaymentService
    data = request.get_json() or {}
    order_id = data.get("order_id")
    if not order_id:
        return error_response("order_id is required", 400)
    try:
        result = PaymentService().refund_order(current_user.id, order_id)
        return success_response(result, "Refund processed")
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@payments_bp.route("/history", methods=["GET"])
@require_auth
def payment_history(current_user):
    """GET /api/payments/history — Customer's payment transaction history."""
    from app.services.payment_service import PaymentService
    page = request.args.get("page", 1, type=int)
    try:
        result = PaymentService().get_history(current_user.id, page=page)
        return success_response(result)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)
