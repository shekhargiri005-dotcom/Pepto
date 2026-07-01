"""
services/order_service.py — Order placement, lifecycle, and tracking.
"""
from __future__ import annotations

import logging
import random
import string
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from sqlalchemy import desc

from app.extensions import db
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.cart import CartItem
from app.models.store import Store
from app.models.product import Product
from app.models.delivery_tracking import DeliveryTracking
from app.models.notification import Notification
from app.utils.exceptions import (
    NotFoundError, ValidationError, AuthorizationError, ConflictError
)

logger = logging.getLogger(__name__)

PLATFORM_FEE_PERCENT = 10.0
GST_PERCENT = 5.0


def _generate_order_number() -> str:
    """Generate a short unique order number like PEP-A3F7K."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"PEP-{suffix}"


class OrderService:

    # ── Place order ───────────────────────────────────────────────────────────

    def place_order(self, customer_id: str, data: dict) -> Dict:
        """Create an order from the current cart."""
        # Validate delivery address
        delivery_address = data.get("delivery_address")
        if not delivery_address:
            raise ValidationError("Delivery address is required")

        payment_method = data.get("payment_method", "card")

        # Load cart
        cart_items = CartItem.query.filter_by(customer_id=customer_id).all()
        if not cart_items:
            raise ValidationError("Your cart is empty")

        store = Store.query.get(str(cart_items[0].store_id))
        if not store:
            raise NotFoundError("Store not found")
        if not store.is_open:
            raise ConflictError("This store is currently closed")
        if not store.is_verified:
            raise ConflictError("This store is not verified yet")

        # Build order items snapshot
        items_snapshot = []
        subtotal = 0.0
        for ci in cart_items:
            product = ci.product
            if not product or not product.is_available:
                raise ConflictError(f"'{product.name if product else 'A product'}' is no longer available")
            if product.stock_quantity < ci.quantity:
                raise ConflictError(f"Insufficient stock for '{product.name}'")

            effective_price = product.effective_price
            item_subtotal = effective_price * ci.quantity
            subtotal += item_subtotal
            items_snapshot.append({
                "product_id": str(product.id),
                "product_name": product.name,
                "brand": product.brand,
                "price": effective_price,
                "quantity": ci.quantity,
                "subtotal": round(item_subtotal, 2),
                "unit": product.unit,
                "image": (product.images or [None])[0],
            })

        # Minimum order check
        if subtotal < float(store.min_order_amount):
            raise ValidationError(
                f"Minimum order amount is ₹{store.min_order_amount:.2f}"
            )

        # Pricing
        delivery_fee = float(store.delivery_charge)
        tax = round(subtotal * GST_PERCENT / 100, 2)
        platform_fee = round(subtotal * PLATFORM_FEE_PERCENT / 100, 2)
        total = round(subtotal + delivery_fee + tax, 2)
        estimated_delivery = datetime.now(timezone.utc) + timedelta(minutes=store.avg_delivery_minutes)

        # Create order
        order_number = _generate_order_number()
        while Order.query.filter_by(order_number=order_number).first():
            order_number = _generate_order_number()

        order = Order(
            order_number=order_number,
            customer_id=customer_id,
            store_id=str(store.id),
            status=OrderStatus.pending,
            items=items_snapshot,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            tax=tax,
            platform_fee=platform_fee,
            total=total,
            delivery_address=delivery_address,
            delivery_lat=delivery_address.get("lat"),
            delivery_lng=delivery_address.get("lng"),
            delivery_instructions=data.get("delivery_instructions"),
            payment_method=payment_method,
            payment_status=PaymentStatus.pending,
            estimated_delivery_at=estimated_delivery,
        )
        db.session.add(order)

        # Decrement stock
        for ci in cart_items:
            ci.product.stock_quantity -= ci.quantity
            if ci.product.stock_quantity <= 0:
                ci.product.is_available = False

        # Clear cart
        CartItem.query.filter_by(customer_id=customer_id).delete()

        # Notify store
        store_notification = Notification(
            user_id=str(store.owner_id),
            type="new_order",
            title="New Order Received!",
            message=f"Order {order_number} — ₹{total:.2f}",
            related_entity_type="order",
        )
        db.session.add(store_notification)
        db.session.commit()

        # Push WebSocket notification to store room
        try:
            from app.sockets import notify_new_order
            notify_new_order(str(store.id), self._order_summary(order))
        except Exception:
            pass

        logger.info("Order placed: %s (₹%.2f) by customer %s", order_number, total, customer_id)
        return self._order_detail(order)

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_customer_orders(self, customer_id: str, page: int = 1, status: Optional[str] = None) -> Dict:
        query = Order.query.filter_by(customer_id=customer_id).order_by(desc(Order.created_at))
        if status:
            try:
                query = query.filter(Order.status == OrderStatus(status))
            except ValueError:
                pass
        pagination = query.paginate(page=page, per_page=20, error_out=False)
        return {
            "items": [self._order_summary(o) for o in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "has_next": pagination.has_next,
        }

    def get_store_orders(self, owner_id: str, page: int = 1, status: Optional[str] = None) -> Dict:
        store = Store.query.filter_by(owner_id=owner_id).first()
        if not store:
            raise NotFoundError("Store not found")
        query = Order.query.filter_by(store_id=str(store.id)).order_by(desc(Order.created_at))
        if status:
            try:
                query = query.filter(Order.status == OrderStatus(status))
            except ValueError:
                pass
        pagination = query.paginate(page=page, per_page=20, error_out=False)
        return {
            "items": [self._order_detail(o) for o in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "has_next": pagination.has_next,
        }

    def get_order(self, user_id: str, order_id: str) -> Dict:
        order = Order.query.get(order_id)
        if not order:
            raise NotFoundError("Order not found")
        # Allow customer, store owner, and delivery partner to view
        store = Store.query.get(str(order.store_id))
        is_customer = str(order.customer_id) == user_id
        is_store = store and str(store.owner_id) == user_id
        is_partner = str(order.delivery_partner_id) == user_id if order.delivery_partner_id else False
        if not (is_customer or is_store or is_partner):
            raise AuthorizationError("Access denied")
        return self._order_detail(order)

    def get_tracking_info(self, user_id: str, order_id: str) -> Dict:
        order = self.get_order(user_id, order_id)
        tracking_logs = DeliveryTracking.query.filter_by(order_id=order_id).order_by(
            DeliveryTracking.timestamp.desc()
        ).limit(1).first()

        partner_location = None
        if tracking_logs:
            partner_location = {"lat": tracking_logs.lat, "lng": tracking_logs.lng}
        elif order.get("delivery_partner_id"):
            from app.models.delivery_partner import DeliveryPartner
            partner = DeliveryPartner.query.get(order["delivery_partner_id"])
            if partner and partner.current_lat:
                partner_location = {"lat": partner.current_lat, "lng": partner.current_lng}

        return {
            "order_id": order_id,
            "status": order["status"],
            "order_number": order["order_number"],
            "estimated_delivery_at": order.get("estimated_delivery_at"),
            "delivery_address": order.get("delivery_address"),
            "partner_location": partner_location,
            "store_lat": None,  # populated by store model if needed
            "store_lng": None,
        }

    # ── Status updates ────────────────────────────────────────────────────────

    def update_order_status(self, owner_id: str, order_id: str, status: str) -> Dict:
        order = Order.query.get(order_id)
        if not order:
            raise NotFoundError("Order not found")

        store = Store.query.filter_by(id=str(order.store_id), owner_id=owner_id).first()
        if not store:
            raise AuthorizationError("You do not own this order's store")

        try:
            new_status = OrderStatus(status)
        except ValueError:
            raise ValidationError(f"Invalid status: {status}")

        order.status = new_status
        if new_status == OrderStatus.confirmed:
            order.confirmed_at = datetime.now(timezone.utc)

        # Notify customer
        db.session.add(Notification(
            user_id=str(order.customer_id),
            type=f"order_{status}",
            title=f"Order Update",
            message=f"Your order {order.order_number} is now {status.replace('_', ' ')}",
            related_entity_type="order",
            related_entity_id=order_id,
        ))
        db.session.commit()

        # Push WebSocket
        try:
            from app.sockets import notify_order_status
            notify_order_status(order_id, status)
        except Exception:
            pass

        return self._order_detail(order)

    def cancel_order(self, customer_id: str, order_id: str, reason: Optional[str] = None) -> Dict:
        order = Order.query.get(order_id)
        if not order:
            raise NotFoundError("Order not found")
        if str(order.customer_id) != customer_id:
            raise AuthorizationError("Access denied")

        cancellable = {OrderStatus.pending, OrderStatus.confirmed}
        if order.status not in cancellable:
            raise ConflictError(f"Cannot cancel an order with status '{order.status.value}'")

        order.status = OrderStatus.cancelled
        order.cancelled_at = datetime.now(timezone.utc)
        order.cancellation_reason = reason or "Cancelled by customer"

        # Restore stock
        for item in (order.items or []):
            product = Product.query.get(item.get("product_id"))
            if product:
                product.stock_quantity += item.get("quantity", 1)
                product.is_available = True

        db.session.commit()
        logger.info("Order cancelled: %s by customer %s", order.order_number, customer_id)
        return self._order_detail(order)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _order_summary(self, o: Order) -> Dict:
        return {
            "id": str(o.id),
            "order_number": o.order_number,
            "store_id": str(o.store_id),
            "status": o.status.value if o.status else None,
            "total": float(o.total),
            "payment_status": o.payment_status.value if o.payment_status else None,
            "item_count": len(o.items or []),
            "estimated_delivery_at": o.estimated_delivery_at.isoformat() if o.estimated_delivery_at else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }

    def _order_detail(self, o: Order) -> Dict:
        d = self._order_summary(o)
        d.update({
            "customer_id": str(o.customer_id),
            "delivery_partner_id": str(o.delivery_partner_id) if o.delivery_partner_id else None,
            "items": o.items or [],
            "subtotal": float(o.subtotal),
            "delivery_fee": float(o.delivery_fee),
            "tax": float(o.tax),
            "platform_fee": float(o.platform_fee),
            "delivery_address": o.delivery_address,
            "delivery_instructions": o.delivery_instructions,
            "payment_method": o.payment_method.value if o.payment_method else None,
            "razorpay_order_id": o.razorpay_order_id,
            "confirmed_at": o.confirmed_at.isoformat() if o.confirmed_at else None,
            "picked_up_at": o.picked_up_at.isoformat() if o.picked_up_at else None,
            "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
            "cancelled_at": o.cancelled_at.isoformat() if o.cancelled_at else None,
            "cancellation_reason": o.cancellation_reason,
        })
        return d
