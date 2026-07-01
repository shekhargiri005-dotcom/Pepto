"""app/api/cart.py — Shopping cart endpoints."""

from flask import Blueprint, request
from app.utils.helpers import success_response, error_response
from app.utils.decorators import require_auth
from app.utils.exceptions import PeptoException
import logging

logger = logging.getLogger(__name__)
cart_bp = Blueprint("cart_bp", __name__)


@cart_bp.route("", methods=["GET"])
@require_auth
def get_cart(current_user):
    """GET /api/cart — Get the current customer's cart with totals."""
    from app.services.cart_service import CartService
    try:
        cart = CartService().get_cart(current_user.id)
        return success_response(cart)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@cart_bp.route("", methods=["POST"])
@require_auth
def add_to_cart(current_user):
    """POST /api/cart — Add a product to the cart.

    If the product belongs to a different store than existing cart items,
    the cart is cleared first (Swiggy/Zomato behaviour).
    """
    from app.services.cart_service import CartService
    data = request.get_json()
    if not data or not data.get("product_id"):
        return error_response("product_id is required", 400)
    try:
        cart = CartService().add_item(
            current_user.id,
            data["product_id"],
            data.get("quantity", 1),
        )
        return success_response(cart, "Item added to cart")
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@cart_bp.route("/<string:item_id>", methods=["PUT"])
@require_auth
def update_cart_item(current_user, item_id):
    """PUT /api/cart/:item_id — Update quantity of a cart item."""
    from app.services.cart_service import CartService
    data = request.get_json() or {}
    quantity = data.get("quantity")
    if quantity is None:
        return error_response("quantity is required", 400)
    try:
        cart = CartService().update_item(current_user.id, item_id, quantity)
        return success_response(cart)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@cart_bp.route("/<string:item_id>", methods=["DELETE"])
@require_auth
def remove_cart_item(current_user, item_id):
    """DELETE /api/cart/:item_id — Remove an item from the cart."""
    from app.services.cart_service import CartService
    try:
        cart = CartService().remove_item(current_user.id, item_id)
        return success_response(cart)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@cart_bp.route("", methods=["DELETE"])
@require_auth
def clear_cart(current_user):
    """DELETE /api/cart — Clear the entire cart."""
    from app.services.cart_service import CartService
    try:
        CartService().clear_cart(current_user.id)
        return success_response(None, "Cart cleared")
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)
