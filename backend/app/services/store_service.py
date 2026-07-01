"""
services/store_service.py — Business logic for pet food store management.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from python_slugify import slugify
from sqlalchemy import func, desc
from geoalchemy2.functions import ST_DWithin, ST_MakePoint

from app.extensions import db
from app.models.store import Store
from app.models.order import Order, OrderStatus
from app.models.review import Review
from app.models.product import Product
from app.utils.exceptions import NotFoundError, ValidationError, AuthorizationError, ConflictError

logger = logging.getLogger(__name__)

PLATFORM_FEE_PERCENT = 10.0


class StoreService:

    # ── Search ────────────────────────────────────────────────────────────────

    def search_stores(
        self,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_km: float = 10.0,
        city: Optional[str] = None,
        q: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict:
        query = Store.query.filter_by(is_verified=True)

        # Geospatial filter
        if lat is not None and lng is not None:
            point = ST_MakePoint(lng, lat)
            query = query.filter(
                ST_DWithin(Store.location, func.ST_SetSRID(point, 4326), radius_km * 1000)
            )
        elif city:
            query = query.filter(Store.city.ilike(f"%{city}%"))

        if q:
            query = query.filter(Store.name.ilike(f"%{q}%"))

        query = query.order_by(desc(Store.avg_rating))
        pagination = query.paginate(page=page, per_page=min(per_page, 50), error_out=False)

        return {
            "items": [self._store_summary(s) for s in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
        }

    def get_store(self, store_id: str) -> Dict:
        store = Store.query.get(store_id)
        if not store:
            raise NotFoundError("Store not found")
        return self._store_detail(store)

    def get_store_reviews(self, store_id: str, page: int = 1) -> Dict:
        store = Store.query.get(store_id)
        if not store:
            raise NotFoundError("Store not found")
        pagination = Review.query.filter_by(store_id=store_id).order_by(
            desc(Review.created_at)
        ).paginate(page=page, per_page=20, error_out=False)
        return {
            "items": [r.to_dict() for r in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "has_next": pagination.has_next,
        }

    # ── Management ────────────────────────────────────────────────────────────

    def create_store(self, owner_id: str, data: dict) -> Dict:
        name = data.get("name", "").strip()
        if not name:
            raise ValidationError("Store name is required")

        # Ensure one store per owner
        existing = Store.query.filter_by(owner_id=owner_id).first()
        if existing:
            raise ConflictError("You already have a store registered")

        slug = slugify(name)
        # Make slug unique
        if Store.query.filter_by(slug=slug).first():
            slug = f"{slug}-{owner_id[:6]}"

        store = Store(
            owner_id=owner_id,
            name=name,
            slug=slug,
            description=data.get("description"),
            address=data.get("address"),
            city=data.get("city"),
            state=data.get("state"),
            phone=data.get("phone"),
            email=data.get("email"),
            delivery_radius_km=data.get("delivery_radius_km", 5.0),
            min_order_amount=data.get("min_order_amount", 0.0),
            delivery_charge=data.get("delivery_charge", 0.0),
            avg_delivery_minutes=data.get("avg_delivery_minutes", 30),
        )

        # Set geospatial point if coordinates provided
        lat = data.get("lat")
        lng = data.get("lng")
        if lat is not None and lng is not None:
            store.lat = lat
            store.lng = lng
            store.location = f"SRID=4326;POINT({lng} {lat})"

        db.session.add(store)
        db.session.commit()
        logger.info("Store created: %s by owner %s", store.id, owner_id)
        return self._store_detail(store)

    def update_store(self, owner_id: str, store_id: str, data: dict) -> Dict:
        store = self._get_owned_store(owner_id, store_id)
        updatable = [
            "name", "description", "address", "city", "state", "phone",
            "email", "delivery_radius_km", "min_order_amount", "delivery_charge",
            "avg_delivery_minutes", "logo_url", "cover_image_url",
        ]
        for field in updatable:
            if field in data:
                setattr(store, field, data[field])

        lat = data.get("lat")
        lng = data.get("lng")
        if lat is not None and lng is not None:
            store.lat = lat
            store.lng = lng
            store.location = f"SRID=4326;POINT({lng} {lat})"

        db.session.commit()
        return self._store_detail(store)

    def toggle_availability(self, owner_id: str, store_id: str, is_open: Optional[bool]) -> Dict:
        store = self._get_owned_store(owner_id, store_id)
        store.is_open = not store.is_open if is_open is None else is_open
        db.session.commit()
        return {"is_open": store.is_open, "store_id": store_id}

    def get_analytics(self, owner_id: str, store_id: str, period: str = "week") -> Dict:
        store = self._get_owned_store(owner_id, store_id)

        days = {"day": 1, "week": 7, "month": 30}.get(period, 7)
        since = datetime.utcnow() - timedelta(days=days)

        orders = Order.query.filter(
            Order.store_id == store_id,
            Order.status == OrderStatus.delivered,
            Order.created_at >= since,
        ).all()

        revenue = sum(float(o.total) for o in orders)
        platform_fee = sum(float(o.platform_fee) for o in orders)

        # Top products from order items
        product_counts: Dict[str, int] = {}
        for order in orders:
            for item in (order.items or []):
                pid = item.get("product_id", "")
                product_counts[pid] = product_counts.get(pid, 0) + item.get("quantity", 1)

        top_product_ids = sorted(product_counts, key=lambda k: product_counts[k], reverse=True)[:5]
        top_products = []
        for pid in top_product_ids:
            p = Product.query.get(pid)
            if p:
                top_products.append({"name": p.name, "orders": product_counts[pid]})

        return {
            "period": period,
            "total_orders": len(orders),
            "revenue": round(revenue, 2),
            "platform_fee": round(platform_fee, 2),
            "net_earnings": round(revenue - platform_fee, 2),
            "avg_order_value": round(revenue / len(orders), 2) if orders else 0,
            "top_products": top_products,
            "store_rating": store.avg_rating,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_owned_store(self, owner_id: str, store_id: str) -> Store:
        store = Store.query.filter_by(id=store_id, owner_id=owner_id).first()
        if not store:
            raise NotFoundError("Store not found or you do not own it")
        return store

    def _store_summary(self, store: Store) -> Dict:
        return {
            "id": str(store.id),
            "name": store.name,
            "slug": store.slug,
            "logo_url": store.logo_url,
            "city": store.city,
            "avg_rating": store.avg_rating,
            "total_orders": store.total_orders,
            "is_open": store.is_open,
            "is_verified": store.is_verified,
            "delivery_charge": float(store.delivery_charge),
            "avg_delivery_minutes": store.avg_delivery_minutes,
            "min_order_amount": float(store.min_order_amount),
        }

    def _store_detail(self, store: Store) -> Dict:
        d = self._store_summary(store)
        d.update({
            "description": store.description,
            "cover_image_url": store.cover_image_url,
            "address": store.address,
            "state": store.state,
            "phone": store.phone,
            "email": store.email,
            "lat": store.lat,
            "lng": store.lng,
            "delivery_radius_km": store.delivery_radius_km,
            "open_time": str(store.open_time) if store.open_time else None,
            "close_time": str(store.close_time) if store.close_time else None,
            "owner_id": str(store.owner_id),
            "created_at": store.created_at.isoformat() if store.created_at else None,
        })
        return d
