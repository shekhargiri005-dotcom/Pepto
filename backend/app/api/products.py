"""app/api/products.py — Product catalog endpoints."""

from flask import Blueprint, request
from app.utils.helpers import success_response, error_response
from app.utils.decorators import require_auth, require_role
from app.utils.exceptions import PeptoException
import logging

logger = logging.getLogger(__name__)
products_bp = Blueprint("products_bp", __name__)


@products_bp.route("/search", methods=["GET"])
def search_products():
    """GET /api/products/search — Full-text + filter product search."""
    from app.services.product_service import ProductService
    params = {
        "q": request.args.get("q"),
        "species": request.args.get("species"),
        "category": request.args.get("category"),
        "brand": request.args.get("brand"),
        "min_price": request.args.get("min_price", type=float),
        "max_price": request.args.get("max_price", type=float),
        "min_rating": request.args.get("min_rating", type=float),
        "store_id": request.args.get("store_id"),
        "page": request.args.get("page", 1, type=int),
        "per_page": request.args.get("per_page", 20, type=int),
        "sort": request.args.get("sort", "relevance"),  # relevance|price_asc|price_desc|rating
    }
    try:
        result = ProductService().search_products(**params)
        return success_response(result)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@products_bp.route("/categories", methods=["GET"])
def get_categories():
    """GET /api/products/categories — All available product categories."""
    from app.models.product import ProductCategory
    return success_response([c.value for c in ProductCategory])


@products_bp.route("/recommended", methods=["GET"])
@require_auth
def get_recommended(current_user):
    """GET /api/products/recommended — Products recommended for user's pets."""
    from app.services.product_service import ProductService
    try:
        result = ProductService().get_recommended(current_user.id)
        return success_response(result)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@products_bp.route("/<string:product_id>", methods=["GET"])
def get_product(product_id):
    """GET /api/products/:id — Product detail."""
    from app.services.product_service import ProductService
    try:
        product = ProductService().get_product(product_id)
        return success_response(product)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@products_bp.route("", methods=["POST"])
@require_auth
@require_role("store_owner")
def create_product(current_user):
    """POST /api/products — Create a product (store_owner only)."""
    from app.services.product_service import ProductService
    data = request.get_json()
    try:
        product = ProductService().create_product(current_user.id, data)
        return success_response(product, "Product created", 201)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@products_bp.route("/<string:product_id>", methods=["PUT"])
@require_auth
@require_role("store_owner")
def update_product(current_user, product_id):
    """PUT /api/products/:id — Update a product (store_owner only)."""
    from app.services.product_service import ProductService
    data = request.get_json()
    try:
        product = ProductService().update_product(current_user.id, product_id, data)
        return success_response(product)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@products_bp.route("/<string:product_id>", methods=["DELETE"])
@require_auth
@require_role("store_owner")
def delete_product(current_user, product_id):
    """DELETE /api/products/:id — Delete a product (store_owner only)."""
    from app.services.product_service import ProductService
    try:
        ProductService().delete_product(current_user.id, product_id)
        return success_response(None, "Product deleted")
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)


@products_bp.route("/<string:product_id>/stock", methods=["PUT"])
@require_auth
@require_role("store_owner")
def update_stock(current_user, product_id):
    """PUT /api/products/:id/stock — Update inventory stock level."""
    from app.services.product_service import ProductService
    data = request.get_json() or {}
    try:
        product = ProductService().update_stock(current_user.id, product_id,
                                                data.get("quantity"), data.get("reason"))
        return success_response(product)
    except PeptoException as exc:
        return error_response(exc.message, exc.status_code, exc.error_code)
