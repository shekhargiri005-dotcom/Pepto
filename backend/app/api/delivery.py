"""app/api/delivery.py — Delivery partner endpoints."""

from flask import Blueprint, request
from app.utils.helpers import success_response, error_response
from app.utils.decorators import require_auth, require_role
from app.utils.exceptions import PeptoException
import logging

logger = logging.getLogger(__name__)
delivery_bp = Blueprint("delivery_bp", __name__)


@delivery_bp.route("/available", methods=["GET"])
@require_auth
@require_role("delivery_partner")
def get_available_orders(current_user):
    """GET /api/delivery/available — Orders available for pickup near the partner."""
    from app.services.delivery_service import DeliveryService
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    try:
        orders = DeliveryService().get_available_orders(current_user.id, lat=lat, lng=lng)
        return success_response(orders)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@delivery_bp.route("/<string:order_id>/accept", methods=["POST"])
@require_auth
@require_role("delivery_partner")
def accept_order(current_user, order_id):
    """POST /api/delivery/:order_id/accept — Accept a delivery assignment."""
    from app.services.delivery_service import DeliveryService
    try:
        result = DeliveryService().accept_order(current_user.id, order_id)
        return success_response(result, "Delivery accepted")
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@delivery_bp.route("/<string:order_id>/location", methods=["PUT"])
@require_auth
@require_role("delivery_partner")
def update_location(current_user, order_id):
    """PUT /api/delivery/:order_id/location — Update GPS location (REST fallback for WebSocket)."""
    from app.services.delivery_service import DeliveryService
    data = request.get_json() or {}
    lat = data.get("lat")
    lng = data.get("lng")
    if lat is None or lng is None:
        return error_response("lat and lng are required", 400)
    try:
        DeliveryService().update_location(current_user.id, order_id, lat, lng)
        return success_response({"lat": lat, "lng": lng})
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@delivery_bp.route("/<string:order_id>/status", methods=["PUT"])
@require_auth
@require_role("delivery_partner")
def update_delivery_status(current_user, order_id):
    """PUT /api/delivery/:order_id/status — Update delivery status."""
    from app.services.delivery_service import DeliveryService
    data = request.get_json() or {}
    status = data.get("status")
    if not status:
        return error_response("status is required", 400)
    try:
        result = DeliveryService().update_status(current_user.id, order_id, status)
        return success_response(result)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@delivery_bp.route("/history", methods=["GET"])
@require_auth
@require_role("delivery_partner")
def delivery_history(current_user):
    """GET /api/delivery/history — Completed delivery history for partner."""
    from app.services.delivery_service import DeliveryService
    page = request.args.get("page", 1, type=int)
    try:
        result = DeliveryService().get_history(current_user.id, page=page)
        return success_response(result)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@delivery_bp.route("/earnings", methods=["GET"])
@require_auth
@require_role("delivery_partner")
def earnings(current_user):
    """GET /api/delivery/earnings — Partner earnings summary."""
    from app.services.delivery_service import DeliveryService
    period = request.args.get("period", "week")
    try:
        result = DeliveryService().get_earnings(current_user.id, period=period)
        return success_response(result)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@delivery_bp.route("/toggle-online", methods=["POST"])
@require_auth
@require_role("delivery_partner")
def toggle_online(current_user):
    """POST /api/delivery/toggle-online — Go online or offline."""
    from app.services.delivery_service import DeliveryService
    data = request.get_json() or {}
    try:
        result = DeliveryService().toggle_online(current_user.id, data.get("is_online"))
        return success_response(result)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)
