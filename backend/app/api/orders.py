"""app/api/orders.py — Order placement and management endpoints."""

from flask import Blueprint, request
from app.utils.helpers import success_response, error_response
from app.utils.decorators import require_auth, require_role
from app.utils.exceptions import PeptoException
import logging

logger = logging.getLogger(__name__)
orders_bp = Blueprint("orders_bp", __name__)


@orders_bp.route("", methods=["POST"])
@require_auth
def place_order(current_user):
    """POST /api/orders — Place a new order from the cart."""
    from app.services.order_service import OrderService
    data = request.get_json()
    try:
        order = OrderService().place_order(current_user.id, data)
        return success_response(order, "Order placed successfully", 201)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@orders_bp.route("", methods=["GET"])
@require_auth
def list_customer_orders(current_user):
    """GET /api/orders — Customer's order history."""
    from app.services.order_service import OrderService
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status")
    try:
        result = OrderService().get_customer_orders(current_user.id, page=page, status=status)
        return success_response(result)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@orders_bp.route("/store", methods=["GET"])
@require_auth
@require_role("store_owner")
def list_store_orders(current_user):
    """GET /api/orders/store — Incoming orders for the store owner's store."""
    from app.services.order_service import OrderService
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status")
    try:
        result = OrderService().get_store_orders(current_user.id, page=page, status=status)
        return success_response(result)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@orders_bp.route("/<string:order_id>", methods=["GET"])
@require_auth
def get_order(current_user, order_id):
    """GET /api/orders/:id — Order detail."""
    from app.services.order_service import OrderService
    try:
        order = OrderService().get_order(current_user.id, order_id)
        return success_response(order)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@orders_bp.route("/<string:order_id>/status", methods=["PUT"])
@require_auth
@require_role("store_owner")
def update_order_status(current_user, order_id):
    """PUT /api/orders/:id/status — Update order status (store_owner only)."""
    from app.services.order_service import OrderService
    data = request.get_json() or {}
    status = data.get("status")
    if not status:
        return error_response("status is required", 400)
    try:
        order = OrderService().update_order_status(current_user.id, order_id, status)
        return success_response(order)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@orders_bp.route("/<string:order_id>/cancel", methods=["POST"])
@require_auth
def cancel_order(current_user, order_id):
    """POST /api/orders/:id/cancel — Customer cancels an order."""
    from app.services.order_service import OrderService
    data = request.get_json() or {}
    try:
        order = OrderService().cancel_order(current_user.id, order_id, data.get("reason"))
        return success_response(order, "Order cancelled")
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@orders_bp.route("/<string:order_id>/tracking", methods=["GET"])
@require_auth
def get_order_tracking(current_user, order_id):
    """GET /api/orders/:id/tracking — Live tracking info for an order."""
    from app.services.order_service import OrderService
    try:
        tracking = OrderService().get_tracking_info(current_user.id, order_id)
        return success_response(tracking)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)
