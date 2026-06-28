"""
app/services/search_service.py
Search service for Pepto marketplace.
Uses PostGIS ST_DWithin for geo-proximity queries and Redis for result caching.
"""

from __future__ import annotations

import json
import logging
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any

from flask import current_app
from sqlalchemy import text, func, and_, or_
from sqlalchemy.orm import joinedload

from app.extensions import db, redis_client
from app.models.provider import ProviderProfile
from app.models.service import Service
from app.models.review import Review
from app.models.booking import Booking
from app.utils.errors import ValidationError, NotFoundError
from app.utils.schemas import SearchQuery

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 300  # 5 minutes
CACHE_KEY_PREFIX = "search:"
PROVIDER_DETAIL_TTL = 120  # 2 minutes
NEARBY_CITY_TTL = 600  # 10 minutes
DEFAULT_RADIUS_KM = 10.0
MAX_RADIUS_KM = 100.0
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50


class SearchService:
    """
    Handles provider discovery using PostGIS geospatial queries,
    category/rating filters, and Redis result caching.
    """

    # ──────────────────────────────────────────────────────────────────────
    # Primary search
    # ──────────────────────────────────────────────────────────────────────

    def search_providers(self, params: SearchQuery) -> dict:
        """
        Search providers by location with optional filters.

        Args:
            params: validated SearchQuery dataclass/pydantic model.

        Returns:
            {providers: [], total, page, per_page, total_pages, cached}
        """
        # ── Build cache key ───────────────────────────────────────────────
        cache_key = self._build_cache_key(params)

        # ── Cache hit ─────────────────────────────────────────────────────
        cached = self._get_cached(cache_key)
        if cached is not None:
            cached["cached"] = True
            return cached

        # ── Validate radius ───────────────────────────────────────────────
        radius_km = float(params.radius_km or DEFAULT_RADIUS_KM)
        if radius_km > MAX_RADIUS_KM:
            raise ValidationError(f"Radius cannot exceed {MAX_RADIUS_KM} km.")
        radius_meters = radius_km * 1000

        lat = float(params.lat)
        lng = float(params.lng)
        page = max(int(params.page or 1), 1)
        per_page = min(int(params.per_page or DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE)
        offset = (page - 1) * per_page

        # ── Base query — PostGIS distance filter ──────────────────────────
        # We use a raw SQL CTE for clean geo expressions then join ORM models.
        geo_point = f"ST_MakePoint({lng}, {lat})::geography"

        query = (
            db.session.query(
                ProviderProfile,
                func.ST_Distance(
                    ProviderProfile.location,
                    text(geo_point),
                ).label("distance_m"),
            )
            .filter(ProviderProfile.is_active == True)  # noqa: E712
            .filter(ProviderProfile.is_verified == True)  # noqa: E712
            .filter(
                func.ST_DWithin(
                    ProviderProfile.location,
                    text(geo_point),
                    radius_meters,
                )
            )
        )

        # ── Category filter (join to services) ────────────────────────────
        if params.category:
            query = query.join(
                Service,
                and_(
                    Service.provider_id == ProviderProfile.id,
                    Service.category == params.category,
                    Service.is_active == True,  # noqa: E712
                ),
            )

        # ── Rating filter ─────────────────────────────────────────────────
        if params.min_rating is not None:
            query = query.filter(ProviderProfile.avg_rating >= float(params.min_rating))

        # ── Price range filter ────────────────────────────────────────────
        if params.min_price is not None or params.max_price is not None:
            query = query.join(
                Service,
                Service.provider_id == ProviderProfile.id,
                isouter=True,
            )
            if params.min_price is not None:
                query = query.filter(Service.price >= float(params.min_price))
            if params.max_price is not None:
                query = query.filter(Service.price <= float(params.max_price))

        # ── Total count ───────────────────────────────────────────────────
        total = query.count()
        total_pages = max((total + per_page - 1) // per_page, 1)

        # ── Ordering + pagination ─────────────────────────────────────────
        results = (
            query.order_by(text("distance_m ASC"), ProviderProfile.avg_rating.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )

        # ── Serialize ─────────────────────────────────────────────────────
        providers_data = [
            self._serialize_provider_summary(profile, dist_m)
            for profile, dist_m in results
        ]

        response = {
            "providers": providers_data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "cached": False,
        }

        # ── Cache and return ──────────────────────────────────────────────
        self._set_cached(cache_key, response, CACHE_TTL_SECONDS)
        return response

    # ──────────────────────────────────────────────────────────────────────
    # Provider detail
    # ──────────────────────────────────────────────────────────────────────

    def get_provider_detail(self, provider_id: str) -> dict:
        """
        Full provider info: profile + services + recent reviews + availability.

        Raises:
            NotFoundError: provider not found or inactive.
        """
        cache_key = f"{CACHE_KEY_PREFIX}detail:{provider_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        provider: Optional[ProviderProfile] = (
            ProviderProfile.query.options(
                joinedload(ProviderProfile.services),
                joinedload(ProviderProfile.availability_slots),
                joinedload(ProviderProfile.user),
            )
            .filter_by(id=provider_id, is_active=True)
            .first()
        )
        if not provider:
            raise NotFoundError(f"Provider '{provider_id}' not found.")

        # ── Recent reviews (last 10) ───────────────────────────────────────
        recent_reviews = (
            Review.query.filter_by(provider_id=provider_id)
            .order_by(Review.created_at.desc())
            .limit(10)
            .all()
        )

        data = self._serialize_provider_detail(provider, recent_reviews)
        self._set_cached(cache_key, data, PROVIDER_DETAIL_TTL)
        return data

    # ──────────────────────────────────────────────────────────────────────
    # City-based fallback
    # ──────────────────────────────────────────────────────────────────────

    def get_nearby_providers_by_city(
        self, city: str, category: Optional[str] = None
    ) -> list:
        """
        Fallback search without coordinates — filter providers by city string.

        Returns list of serialized provider summaries.
        """
        cache_key = f"{CACHE_KEY_PREFIX}city:{city.lower()}:{category or 'all'}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        query = ProviderProfile.query.filter(
            ProviderProfile.is_active == True,  # noqa: E712
            ProviderProfile.is_verified == True,  # noqa: E712
            func.lower(ProviderProfile.city) == city.strip().lower(),
        )

        if category:
            query = query.join(
                Service,
                and_(
                    Service.provider_id == ProviderProfile.id,
                    Service.category == category,
                    Service.is_active == True,  # noqa: E712
                ),
            )

        providers = (
            query.order_by(ProviderProfile.avg_rating.desc()).limit(50).all()
        )

        result: List[dict] = [
            self._serialize_provider_summary(p, None) for p in providers
        ]
        self._set_cached(cache_key, result, NEARBY_CITY_TTL)
        return result

    # ──────────────────────────────────────────────────────────────────────
    # Cache helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_cache_key(params: SearchQuery) -> str:
        raw = (
            f"lat={params.lat}"
            f"|lng={params.lng}"
            f"|r={params.radius_km}"
            f"|cat={params.category}"
            f"|min_r={params.min_rating}"
            f"|min_p={params.min_price}"
            f"|max_p={params.max_price}"
            f"|page={params.page}"
            f"|pp={params.per_page}"
        )
        digest = hashlib.md5(raw.encode()).hexdigest()
        return f"{CACHE_KEY_PREFIX}{digest}"

    @staticmethod
    def _get_cached(key: str) -> Optional[Any]:
        try:
            raw = redis_client.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            logger.warning("Redis get failed for key %s", key)
        return None

    @staticmethod
    def _set_cached(key: str, value: Any, ttl: int) -> None:
        try:
            redis_client.setex(key, ttl, json.dumps(value, default=str))
        except Exception:
            logger.warning("Redis set failed for key %s", key)

    # ──────────────────────────────────────────────────────────────────────
    # Serializers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _serialize_provider_summary(
        provider: ProviderProfile, distance_m: Optional[float]
    ) -> dict:
        distance_km = round(distance_m / 1000, 2) if distance_m is not None else None
        return {
            "id": provider.id,
            "business_name": provider.business_name,
            "tagline": provider.tagline,
            "city": provider.city,
            "state": provider.state,
            "avg_rating": float(provider.avg_rating) if provider.avg_rating else None,
            "total_reviews": provider.total_reviews or 0,
            "profile_photo": provider.profile_photo,
            "is_verified": provider.is_verified,
            "distance_km": distance_km,
            "services_count": len(provider.services) if provider.services else 0,
            "years_experience": provider.years_experience,
        }

    @staticmethod
    def _serialize_provider_detail(
        provider: ProviderProfile, recent_reviews: list
    ) -> dict:
        services_data = [
            {
                "id": s.id,
                "name": s.name,
                "category": s.category,
                "description": s.description,
                "price": float(s.price) if s.price else None,
                "duration_minutes": s.duration_minutes,
                "is_active": s.is_active,
            }
            for s in (provider.services or [])
            if s.is_active
        ]

        availability_data = [
            {
                "day_of_week": slot.day_of_week,
                "start_time": slot.start_time.strftime("%H:%M") if slot.start_time else None,
                "end_time": slot.end_time.strftime("%H:%M") if slot.end_time else None,
                "max_concurrent": slot.max_concurrent_bookings,
            }
            for slot in (provider.availability_slots or [])
        ]

        reviews_data = [
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
            for r in recent_reviews
        ]

        user = provider.user
        return {
            "id": provider.id,
            "business_name": provider.business_name,
            "tagline": provider.tagline,
            "bio": provider.bio,
            "city": provider.city,
            "state": provider.state,
            "address": provider.address,
            "avg_rating": float(provider.avg_rating) if provider.avg_rating else None,
            "total_reviews": provider.total_reviews or 0,
            "profile_photo": provider.profile_photo,
            "gallery_photos": provider.gallery_photos or [],
            "is_verified": provider.is_verified,
            "years_experience": provider.years_experience,
            "certifications": provider.certifications or [],
            "contact_email": user.email if user else None,
            "contact_phone": user.phone if user else None,
            "services": services_data,
            "availability": availability_data,
            "recent_reviews": reviews_data,
            "created_at": provider.created_at.isoformat() if provider.created_at else None,
        }
