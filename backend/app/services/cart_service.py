"""
services/cart_service.py — Shopping cart management with single-store enforcement.
"""
from __future__ import annotations

import logging
from typing import Dict, List

from app.extensions import db
from app.models.cart import CartItem
from app.models.product import Product
from app.models.store import Store
from app.utils.exceptions import NotFoundError, ValidationError, ConflictError

logger = logging.getLogger(__name__)


class CartService:

    def get_cart(self, customer_id: str) -> Dict:
        items = CartItem.query.filter_by(customer_id=customer_id).all()
        return self._build_cart_response(items)

    def add_item(self, customer_id: str, product_id: str, quantity: int = 1) -> Dict:
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1")

        product = Product.query.get(product_id)
        if not product:
            raise NotFoundError("Product not found")
        if not product.is_available or product.stock_quantity < quantity:
            raise ValidationError("Product is not available or insufficient stock")

        # Single-store enforcement — clear cart if different store
        existing_items = CartItem.query.filter_by(customer_id=customer_id).all()
        if existing_items and str(existing_items[0].store_id) != str(product.store_id):
            # Clear cart (Swiggy/Zomato behaviour)
            for item in existing_items:
                db.session.delete(item)
            logger.info("Cart cleared for customer %s — switching stores", customer_id)

        # If same product already in cart, increment quantity
        existing = CartItem.query.filter_by(
            customer_id=customer_id, product_id=product_id
        ).first()

        if existing:
            existing.quantity += quantity
        else:
            cart_item = CartItem(
                customer_id=customer_id,
                store_id=str(product.store_id),
                product_id=product_id,
                quantity=quantity,
            )
            db.session.add(cart_item)

        db.session.commit()
        return self.get_cart(customer_id)

    def update_item(self, customer_id: str, item_id: str, quantity: int) -> Dict:
        item = CartItem.query.filter_by(id=item_id, customer_id=customer_id).first()
        if not item:
            raise NotFoundError("Cart item not found")
        if quantity < 1:
            # Remove item if quantity set to 0
            db.session.delete(item)
        else:
            item.quantity = quantity
        db.session.commit()
        return self.get_cart(customer_id)

    def remove_item(self, customer_id: str, item_id: str) -> Dict:
        item = CartItem.query.filter_by(id=item_id, customer_id=customer_id).first()
        if not item:
            raise NotFoundError("Cart item not found")
        db.session.delete(item)
        db.session.commit()
        return self.get_cart(customer_id)

    def clear_cart(self, customer_id: str) -> None:
        CartItem.query.filter_by(customer_id=customer_id).delete()
        db.session.commit()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_cart_response(self, items: List[CartItem]) -> Dict:
        if not items:
            return {"items": [], "store": None, "subtotal": 0.0, "item_count": 0}

        cart_items = []
        subtotal = 0.0
        store_id = None

        for item in items:
            product = item.product
            if not product:
                continue
            effective_price = product.effective_price
            item_subtotal = effective_price * item.quantity
            subtotal += item_subtotal
            store_id = str(item.store_id)
            cart_items.append({
                "id": str(item.id),
                "product_id": str(product.id),
                "product_name": product.name,
                "product_image": (product.images or [None])[0],
                "brand": product.brand,
                "price": float(product.price),
                "discount_price": float(product.discount_price) if product.discount_price else None,
                "effective_price": effective_price,
                "quantity": item.quantity,
                "subtotal": round(item_subtotal, 2),
                "unit": product.unit,
                "stock_quantity": product.stock_quantity,
            })

        store = None
        if store_id:
            s = Store.query.get(store_id)
            if s:
                store = {
                    "id": store_id,
                    "name": s.name,
                    "delivery_charge": float(s.delivery_charge),
                    "min_order_amount": float(s.min_order_amount),
                    "avg_delivery_minutes": s.avg_delivery_minutes,
                    "is_open": s.is_open,
                }

        delivery_charge = float(store["delivery_charge"]) if store else 0.0
        meets_minimum = subtotal >= float(store["min_order_amount"]) if store else True

        return {
            "items": cart_items,
            "store": store,
            "subtotal": round(subtotal, 2),
            "delivery_charge": delivery_charge,
            "total": round(subtotal + delivery_charge, 2),
            "item_count": sum(i["quantity"] for i in cart_items),
            "meets_minimum_order": meets_minimum,
        }
