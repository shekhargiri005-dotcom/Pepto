"""
app/api/providers.py
Providers Blueprint for Pepto marketplace.
Handles provider search, profile management, services, and availability.
"""

from __future__ import annotations

import logging
from flask import Blueprint, request, current_app

from app.services.search_service import SearchService
from app.utils.auth_decorators import require_auth, require_role
from app.utils.response_helpers import success_response, error_response
from app.utils.errors import (
    ValidationError,
    NotFoundError,
    ConflictError,
    ForbiddenError,
)
from app.utils.schemas import SearchQuery

logger = logging.getLogger(__name__)
providers_bp = Blueprint("providers", __name__, url_prefix="/api/providers")
_search_svc = SearchService()


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/providers/search
# ──────────────────────────────────────────────────────────────────────────────
@providers_bp.route("/search", methods=["GET"])
def search_providers():
    """Search for providers by location with optional filters. Results are cached."""
    try:
        args = request.args

        # Require at least lat/lng or city
        lat = args.get("lat")
        lng = args.get("lng")
        city = args.get("city")

        if not (lat and lng) and not city:
            return error_response(
                "Provide either lat/lng coordinates or a city name.", status_code=400
            )

        if lat and lng:
            try:
                lat = float(lat)
                lng = float(lng)
            except ValueError:
                return error_response("lat and lng must be valid numbers.", status_code=400)

            params = SearchQuery(
                lat=lat,
                lng=lng,
                radius_km=float(args.get("radius_km", 10.0)),
                category=args.get("category"),
                min_rating=float(args.get("min_rating")) if args.get("min_rating") else None,
                min_price=float(args.get("min_price")) if args.get("min_price") else None,
                max_price=float(args.get("max_price")) if args.get("max_price") else None,
                page=int(args.get("page", 1)),
                per_page=int(args.get("per_page", 10)),
            )
            result = _search_svc.search_providers(params)
        else:
            result = {"providers": _search_svc.get_nearby_providers_by_city(city, args.get("category"))}

        return success_response(data=result)
    except ValidationError as exc:
        return error_response(str(exc), status_code=422)
    except Exception:
        current_app.logger.exception("Unexpected error in search_providers()")
        return error_response("Search failed. Please try again.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/providers/<id>
# ──────────────────────────────────────────────────────────────────────────────
@providers_bp.route("/<string:provider_id>", methods=["GET"])
def get_provider(provider_id: str):
    """Get full provider details including services and recent reviews."""
    try:
        data = _search_svc.get_provider_detail(provider_id)
        return success_response(data=data)
    except NotFoundError as exc:
        return error_response(str(exc), status_code=404)
    except Exception:
        current_app.logger.exception("Unexpected error in get_provider()")
        return error_response("Failed to load provider.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/providers/profile
# ──────────────────────────────────────────────────────────────────────────────
@providers_bp.route("/profile", methods=["POST"])
@require_auth
@require_role("provider")
def create_profile():
    """Create a new provider profile for the authenticated provider user."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        user = request.current_user

        from app.extensions import db
        from app.models.provider import ProviderProfile
        import uuid

        existing = ProviderProfile.query.filter_by(user_id=user.id).first()
        if existing:
            return error_response("Provider profile already exists.", status_code=409)

        business_name = (data.get("business_name") or "").strip()
        if not business_name:
            return error_response("business_name is required.", status_code=422)

        profile = ProviderProfile(
            id=str(uuid.uuid4()),
            user_id=user.id,
            business_name=business_name,
            tagline=data.get("tagline"),
            bio=data.get("bio"),
            city=data.get("city"),
            state=data.get("state"),
            address=data.get("address"),
            years_experience=data.get("years_experience"),
            certifications=data.get("certifications", []),
            is_active=True,
            is_verified=False,
        )
        db.session.add(profile)
        db.session.commit()
        current_app.logger.info("Provider profile created for user %s", user.id)
        return success_response(
            data={"id": profile.id, "business_name": profile.business_name},
            message="Provider profile created. Verification pending.",
            status_code=201,
        )
    except Exception:
        from app.extensions import db
        db.session.rollback()
        current_app.logger.exception("Unexpected error in create_profile()")
        return error_response("Failed to create provider profile.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# PUT /api/providers/profile
# ──────────────────────────────────────────────────────────────────────────────
@providers_bp.route("/profile", methods=["PUT"])
@require_auth
@require_role("provider")
def update_profile():
    """Update the authenticated provider's profile."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        user = request.current_user

        from app.extensions import db
        from app.models.provider import ProviderProfile

        profile = ProviderProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return error_response("Provider profile not found.", status_code=404)

        updatable = [
            "business_name", "tagline", "bio", "city", "state",
            "address", "years_experience", "certifications", "profile_photo",
        ]
        for field in updatable:
            if field in data:
                setattr(profile, field, data[field])

        db.session.commit()
        return success_response(
            data={"id": profile.id, "business_name": profile.business_name},
            message="Profile updated successfully.",
        )
    except Exception:
        from app.extensions import db
        db.session.rollback()
        current_app.logger.exception("Unexpected error in update_profile()")
        return error_response("Failed to update profile.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/providers/me
# ──────────────────────────────────────────────────────────────────────────────
@providers_bp.route("/me", methods=["GET"])
@require_auth
@require_role("provider")
def get_my_profile():
    """Get the authenticated provider's full profile."""
    try:
        user = request.current_user
        from app.models.provider import ProviderProfile

        profile = ProviderProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return error_response("Provider profile not found.", status_code=404)

        return success_response(data=_search_svc.get_provider_detail(profile.id))
    except Exception:
        current_app.logger.exception("Unexpected error in get_my_profile()")
        return error_response("Failed to retrieve profile.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/providers/services
# ──────────────────────────────────────────────────────────────────────────────
@providers_bp.route("/services", methods=["POST"])
@require_auth
@require_role("provider")
def create_service():
    """Add a new service to the provider's profile."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        user = request.current_user

        from app.extensions import db
        from app.models.provider import ProviderProfile
        from app.models.service import Service
        import uuid

        profile = ProviderProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return error_response("Provider profile not found.", status_code=404)

        name = (data.get("name") or "").strip()
        category = (data.get("category") or "").strip()
        price = data.get("price")
        duration = data.get("duration_minutes")

        if not name or not category or price is None or duration is None:
            return error_response(
                "name, category, price, and duration_minutes are required.", status_code=422
            )

        service = Service(
            id=str(uuid.uuid4()),
            provider_id=profile.id,
            name=name,
            category=category,
            description=data.get("description"),
            price=float(price),
            duration_minutes=int(duration),
            is_active=True,
        )
        db.session.add(service)
        db.session.commit()
        return success_response(
            data={"id": service.id, "name": service.name, "category": service.category},
            message="Service added successfully.",
            status_code=201,
        )
    except Exception:
        from app.extensions import db
        db.session.rollback()
        current_app.logger.exception("Unexpected error in create_service()")
        return error_response("Failed to create service.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# PUT /api/providers/services/<id>
# ──────────────────────────────────────────────────────────────────────────────
@providers_bp.route("/services/<string:service_id>", methods=["PUT"])
@require_auth
@require_role("provider")
def update_service(service_id: str):
    """Update an existing service."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        user = request.current_user

        from app.extensions import db
        from app.models.provider import ProviderProfile
        from app.models.service import Service

        profile = ProviderProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return error_response("Provider profile not found.", status_code=404)

        service = Service.query.filter_by(id=service_id, provider_id=profile.id).first()
        if not service:
            return error_response("Service not found.", status_code=404)

        for field in ["name", "category", "description", "is_active"]:
            if field in data:
                setattr(service, field, data[field])
        if "price" in data:
            service.price = float(data["price"])
        if "duration_minutes" in data:
            service.duration_minutes = int(data["duration_minutes"])

        db.session.commit()
        return success_response(
            data={"id": service.id, "name": service.name},
            message="Service updated successfully.",
        )
    except Exception:
        from app.extensions import db
        db.session.rollback()
        current_app.logger.exception("Unexpected error in update_service()")
        return error_response("Failed to update service.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# DELETE /api/providers/services/<id>
# ──────────────────────────────────────────────────────────────────────────────
@providers_bp.route("/services/<string:service_id>", methods=["DELETE"])
@require_auth
@require_role("provider")
def delete_service(service_id: str):
    """Soft-delete a service (marks as inactive)."""
    try:
        user = request.current_user
        from app.extensions import db
        from app.models.provider import ProviderProfile
        from app.models.service import Service

        profile = ProviderProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return error_response("Provider profile not found.", status_code=404)

        service = Service.query.filter_by(id=service_id, provider_id=profile.id).first()
        if not service:
            return error_response("Service not found.", status_code=404)

        service.is_active = False
        db.session.commit()
        return success_response(message="Service deleted successfully.")
    except Exception:
        from app.extensions import db
        db.session.rollback()
        current_app.logger.exception("Unexpected error in delete_service()")
        return error_response("Failed to delete service.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/providers/services
# ──────────────────────────────────────────────────────────────────────────────
@providers_bp.route("/services", methods=["GET"])
@require_auth
@require_role("provider")
def list_my_services():
    """List all services for the authenticated provider."""
    try:
        user = request.current_user
        from app.models.provider import ProviderProfile
        from app.models.service import Service

        profile = ProviderProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return error_response("Provider profile not found.", status_code=404)

        services = Service.query.filter_by(provider_id=profile.id).all()
        return success_response(
            data=[
                {
                    "id": s.id,
                    "name": s.name,
                    "category": s.category,
                    "description": s.description,
                    "price": float(s.price) if s.price else None,
                    "duration_minutes": s.duration_minutes,
                    "is_active": s.is_active,
                }
                for s in services
            ]
        )
    except Exception:
        current_app.logger.exception("Unexpected error in list_my_services()")
        return error_response("Failed to list services.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/providers/availability
# ──────────────────────────────────────────────────────────────────────────────
@providers_bp.route("/availability", methods=["POST"])
@require_auth
@require_role("provider")
def set_availability():
    """Set or update availability slots for the authenticated provider."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        user = request.current_user
        slots = data.get("slots", [])

        if not isinstance(slots, list) or not slots:
            return error_response("slots must be a non-empty list.", status_code=422)

        from app.extensions import db
        from app.models.provider import ProviderProfile, ProviderAvailability
        from datetime import time
        import uuid

        profile = ProviderProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return error_response("Provider profile not found.", status_code=404)

        # Delete existing slots and recreate
        ProviderAvailability.query.filter_by(provider_id=profile.id).delete()

        created = []
        for slot in slots:
            day_of_week = slot.get("day_of_week")
            start_str = slot.get("start_time")
            end_str = slot.get("end_time")
            max_concurrent = int(slot.get("max_concurrent_bookings", 1))

            if day_of_week is None or not start_str or not end_str:
                return error_response(
                    "Each slot requires day_of_week, start_time, and end_time.", status_code=422
                )

            start_t = time.fromisoformat(start_str)
            end_t = time.fromisoformat(end_str)

            avail = ProviderAvailability(
                id=str(uuid.uuid4()),
                provider_id=profile.id,
                day_of_week=int(day_of_week),
                start_time=start_t,
                end_time=end_t,
                max_concurrent_bookings=max_concurrent,
            )
            db.session.add(avail)
            created.append({"day_of_week": day_of_week, "start_time": start_str, "end_time": end_str})

        db.session.commit()
        return success_response(
            data={"slots": created},
            message=f"{len(created)} availability slot(s) saved.",
        )
    except Exception:
        from app.extensions import db
        db.session.rollback()
        current_app.logger.exception("Unexpected error in set_availability()")
        return error_response("Failed to set availability.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/providers/availability
# ──────────────────────────────────────────────────────────────────────────────
@providers_bp.route("/availability", methods=["GET"])
@require_auth
@require_role("provider")
def get_availability():
    """Get the authenticated provider's availability slots."""
    try:
        user = request.current_user
        from app.models.provider import ProviderProfile, ProviderAvailability

        profile = ProviderProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return error_response("Provider profile not found.", status_code=404)

        slots = ProviderAvailability.query.filter_by(provider_id=profile.id).all()
        return success_response(
            data=[
                {
                    "id": s.id,
                    "day_of_week": s.day_of_week,
                    "start_time": s.start_time.strftime("%H:%M") if s.start_time else None,
                    "end_time": s.end_time.strftime("%H:%M") if s.end_time else None,
                    "max_concurrent_bookings": s.max_concurrent_bookings,
                }
                for s in slots
            ]
        )
    except Exception:
        current_app.logger.exception("Unexpected error in get_availability()")
        return error_response("Failed to retrieve availability.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/providers/<id>/reviews
# ──────────────────────────────────────────────────────────────────────────────
@providers_bp.route("/<string:provider_id>/reviews", methods=["GET"])
def get_reviews(provider_id: str):
    """Get paginated reviews for a provider."""
    try:
        from app.models.review import Review
        from app.models.provider import ProviderProfile

        provider = ProviderProfile.query.filter_by(id=provider_id, is_active=True).first()
        if not provider:
            return error_response("Provider not found.", status_code=404)

        page = int(request.args.get("page", 1))
        per_page = 10

        reviews_q = (
            Review.query.filter_by(provider_id=provider_id)
            .order_by(Review.created_at.desc())
        )
        total = reviews_q.count()
        reviews = reviews_q.offset((page - 1) * per_page).limit(per_page).all()

        return success_response(
            data={
                "reviews": [
                    {
                        "id": r.id,
                        "rating": r.rating,
                        "comment": r.comment,
                        "provider_response": r.provider_response,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "customer_name": (
                            f"{r.customer.first_name} {r.customer.last_name[0]}."
                            if r.customer else "Anonymous"
                        ),
                    }
                    for r in reviews
                ],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": max((total + per_page - 1) // per_page, 1),
                "avg_rating": float(provider.avg_rating) if provider.avg_rating else None,
                "total_reviews": provider.total_reviews or 0,
            }
        )
    except Exception:
        current_app.logger.exception("Unexpected error in get_reviews()")
        return error_response("Failed to retrieve reviews.", status_code=500)
