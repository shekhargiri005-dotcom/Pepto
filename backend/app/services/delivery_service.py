"""
services/delivery_service.py — Delivery partner management and assignment.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from sqlalchemy import desc

from app.extensions import db
from app.models.delivery_partner import DeliveryPartner
from app.models.order import Order, OrderStatus
from app.models.store import Store
from app.models.delivery_tracking import DeliveryTracking
from app.models.notification import Notification
from app.models.user import User
from app.utils.exceptions import NotFoundError, ValidationError, AuthorizationError, ConflictError

logger = logging.getLogger(__name__)

DELIVERY_PARTNER_FEE_PER_ORDER = 40.0  # Base earnings per delivery (INR)


class DeliveryService:

    # ── Partner setup ─────────────────────────────────────────────────────────

    def get_or_create_profile(self, user_id: str) -> DeliveryPartner:
        profile = DeliveryPartner.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = DeliveryPartner(user_id=user_id)
            db.session.add(profile)
            db.session.commit()
        return profile

    def toggle_online(self, user_id: str, is_online: Optional[bool]) -> Dict:
        partner = DeliveryPartner.query.filter_by(user_id=user_id).first()
        if not partner:
            partner = self.get_or_create_profile(user_id)
        partner.is_online = not partner.is_online if is_online is None else is_online
        if not partner.is_online:
            partner.is_available = False
        db.session.commit()
        return {"is_online": partner.is_online, "partner_id": str(partner.id)}

    # ── Order discovery ───────────────────────────────────────────────────────

    def get_available_orders(self, user_id: str, lat: Optional[float] = None, lng: Optional[float] = None) -> List[Dict]:
        """Return orders with status 'ready' that have no delivery partner assigned."""
        partner = DeliveryPartner.query.filter_by(user_id=user_id).first()
        if not partner or not partner.is_online:
            raise ConflictError("You must be online to see available orders")

        query = Order.query.filter(
            Order.status == OrderStatus.ready,
            Order.delivery_partner_id == None,
        ).order_by(Order.created_at)

        orders = query.limit(20).all()
        result = []
        for o in orders:
            store = Store.query.get(str(o.store_id))
            result.append({
                "id": str(o.id),
                "order_number": o.order_number,
                "store_name": store.name if store else "Unknown",
                "store_address": store.address if store else None,
                "store_lat": store.lat if store else None,
                "store_lng": store.lng if store else None,
                "delivery_address": o.delivery_address,
                "item_count": len(o.items or []),
                "total": float(o.total),
                "estimated_earn": DELIVERY_PARTNER_FEE_PER_ORDER,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            })
        return result

    def accept_order(self, user_id: str, order_id: str) -> Dict:
        partner = DeliveryPartner.query.filter_by(user_id=user_id).first()
        if not partner:
            raise NotFoundError("Delivery partner profile not found")
        if not partner.is_online:
            raise ConflictError("You must be online to accept orders")
        if not partner.is_available:
            raise ConflictError("You already have an active delivery")

        order = Order.query.get(order_id)
        if not order:
            raise NotFoundError("Order not found")
        if order.status != OrderStatus.ready:
            raise ConflictError("This order is no longer available for pickup")
        if order.delivery_partner_id:
            raise ConflictError("This order has already been accepted by another partner")

        # Assign
        order.delivery_partner_id = str(partner.id)
        order.status = OrderStatus.picked_up
        order.picked_up_at = datetime.now(timezone.utc)
        partner.current_order_id = str(order.id)
        partner.is_available = False

        # Notify customer
        db.session.add(Notification(
            user_id=str(order.customer_id),
            type="delivery_assigned",
            title="Delivery Partner Assigned",
            message=f"Your order {order.order_number} has been picked up and is on the way!",
            related_entity_type="order",
            related_entity_id=order_id,
        ))
        db.session.commit()

        # WebSocket
        try:
            from app.sockets import notify_order_status
            notify_order_status(order_id, "picked_up", {"partner_id": str(partner.id)})
        except Exception:
            pass

        logger.info("Order %s accepted by partner %s", order.order_number, partner.id)
        return {"order_id": order_id, "status": "picked_up", "partner_id": str(partner.id)}

    # ── Live tracking ─────────────────────────────────────────────────────────

    def update_location(self, user_id: str, order_id: str, lat: float, lng: float) -> None:
        partner = DeliveryPartner.query.filter_by(user_id=user_id).first()
        if not partner:
            raise NotFoundError("Partner profile not found")

        partner.current_lat = lat
        partner.current_lng = lng

        db.session.add(DeliveryTracking(
            order_id=order_id,
            delivery_partner_id=str(partner.id),
            lat=lat,
            lng=lng,
            status="in_transit",
        ))
        db.session.commit()

        # WebSocket broadcast
        try:
            from app.extensions import socketio
            socketio.emit(
                "location_updated",
                {"lat": lat, "lng": lng, "partner_id": str(partner.id), "order_id": order_id},
                room=f"order_{order_id}",
            )
        except Exception:
            pass

    def update_status(self, user_id: str, order_id: str, status: str) -> Dict:
        partner = DeliveryPartner.query.filter_by(user_id=user_id).first()
        if not partner:
            raise NotFoundError("Partner profile not found")

        order = Order.query.filter_by(id=order_id, delivery_partner_id=str(partner.id)).first()
        if not order:
            raise AuthorizationError("This order is not assigned to you")

        try:
            new_status = OrderStatus(status)
        except ValueError:
            raise ValidationError(f"Invalid status: {status}")

        order.status = new_status

        if new_status == OrderStatus.delivered:
            order.delivered_at = datetime.now(timezone.utc)
            partner.current_order_id = None
            partner.is_available = True
            partner.total_deliveries += 1
            partner.total_earnings += DELIVERY_PARTNER_FEE_PER_ORDER

            # Update store total orders counter
            store = Store.query.get(str(order.store_id))
            if store:
                store.total_orders += 1

            # Notify customer
            db.session.add(Notification(
                user_id=str(order.customer_id),
                type="order_delivered",
                title="Order Delivered! 🎉",
                message=f"Your order {order.order_number} has been delivered. Enjoy!",
                related_entity_type="order",
                related_entity_id=order_id,
            ))

        db.session.commit()

        # WebSocket
        try:
            from app.sockets import notify_order_status
            notify_order_status(order_id, status)
        except Exception:
            pass

        logger.info("Order %s → %s by partner %s", order.order_number, status, partner.id)
        return {"order_id": order_id, "status": status}

    # ── History & earnings ────────────────────────────────────────────────────

    def get_history(self, user_id: str, page: int = 1) -> Dict:
        partner = DeliveryPartner.query.filter_by(user_id=user_id).first()
        if not partner:
            return {"items": [], "total": 0}

        pagination = Order.query.filter(
            Order.delivery_partner_id == str(partner.id),
            Order.status == OrderStatus.delivered,
        ).order_by(desc(Order.delivered_at)).paginate(page=page, per_page=20, error_out=False)

        return {
            "items": [
                {
                    "order_id": str(o.id),
                    "order_number": o.order_number,
                    "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
                    "total": float(o.total),
                    "earned": DELIVERY_PARTNER_FEE_PER_ORDER,
                }
                for o in pagination.items
            ],
            "total": pagination.total,
            "page": pagination.page,
            "has_next": pagination.has_next,
        }

    def get_earnings(self, user_id: str, period: str = "week") -> Dict:
        partner = DeliveryPartner.query.filter_by(user_id=user_id).first()
        if not partner:
            return {"total_earnings": 0, "deliveries": 0}

        days = {"day": 1, "week": 7, "month": 30}.get(period, 7)
        since = datetime.now(timezone.utc) - timedelta(days=days)

        orders = Order.query.filter(
            Order.delivery_partner_id == str(partner.id),
            Order.status == OrderStatus.delivered,
            Order.delivered_at >= since,
        ).count()

        return {
            "period": period,
            "deliveries_this_period": orders,
            "earned_this_period": round(orders * DELIVERY_PARTNER_FEE_PER_ORDER, 2),
            "total_deliveries": partner.total_deliveries,
            "total_earnings": float(partner.total_earnings),
            "avg_rating": partner.avg_rating,
            "is_online": partner.is_online,
        }
