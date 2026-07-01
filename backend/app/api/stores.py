"""app/api/stores.py — Store management endpoints."""

from flask import Blueprint, request
from app.utils.helpers import success_response, error_response
from app.utils.decorators import require_auth, require_role, validate_json
from app.utils.exceptions import PeptoException
import logging

logger = logging.getLogger(__name__)
stores_bp = Blueprint("stores_bp", __name__)


@stores_bp.route("", methods=["GET"])
def list_stores():
    """GET /api/stores — List/search stores with optional geo & text filters."""
    from app.services.store_service import StoreService
    service = StoreService()
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    radius_km = request.args.get("radius_km", 10.0, type=float)
    city = request.args.get("city")
    q = request.args.get("q")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    try:
        result = service.search_stores(lat=lat, lng=lng, radius_km=radius_km,
                                       city=city, q=q, page=page, per_page=per_page)
        return success_response(result)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@stores_bp.route("/<string:store_id>", methods=["GET"])
def get_store(store_id):
    """GET /api/stores/:id — Store detail."""
    from app.services.store_service import StoreService
    try:
        store = StoreService().get_store(store_id)
        return success_response(store)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@stores_bp.route("/<string:store_id>/products", methods=["GET"])
def get_store_products(store_id):
    """GET /api/stores/:id/products — Products for a specific store."""
    from app.services.product_service import ProductService
    page = request.args.get("page", 1, type=int)
    category = request.args.get("category")
    try:
        result = ProductService().get_store_products(store_id, page=page, category=category)
        return success_response(result)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@stores_bp.route("/<string:store_id>/reviews", methods=["GET"])
def get_store_reviews(store_id):
    """GET /api/stores/:id/reviews — Reviews for a store."""
    from app.services.store_service import StoreService
    page = request.args.get("page", 1, type=int)
    try:
        result = StoreService().get_store_reviews(store_id, page=page)
        return success_response(result)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@stores_bp.route("", methods=["POST"])
@require_auth
@require_role("store_owner")
def create_store(current_user):
    """POST /api/stores — Create a store (store_owner only)."""
    from app.services.store_service import StoreService
    data = request.get_json()
    try:
        store = StoreService().create_store(current_user.id, data)
        return success_response(store, "Store created successfully", 201)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@stores_bp.route("/<string:store_id>", methods=["PUT"])
@require_auth
@require_role("store_owner")
def update_store(current_user, store_id):
    """PUT /api/stores/:id — Update store (store_owner only)."""
    from app.services.store_service import StoreService
    data = request.get_json()
    try:
        store = StoreService().update_store(current_user.id, store_id, data)
        return success_response(store, "Store updated successfully")
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@stores_bp.route("/<string:store_id>/availability", methods=["PUT"])
@require_auth
@require_role("store_owner")
def toggle_availability(current_user, store_id):
    """PUT /api/stores/:id/availability — Toggle store open/closed."""
    from app.services.store_service import StoreService
    data = request.get_json() or {}
    try:
        store = StoreService().toggle_availability(current_user.id, store_id, data.get("is_open"))
        return success_response(store)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@stores_bp.route("/<string:store_id>/analytics", methods=["GET"])
@require_auth
@require_role("store_owner")
def get_store_analytics(current_user, store_id):
    """GET /api/stores/:id/analytics — Sales analytics (store_owner only)."""
    from app.services.store_service import StoreService
    period = request.args.get("period", "week")  # day / week / month
    try:
        data = StoreService().get_analytics(current_user.id, store_id, period)
        return success_response(data)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)
