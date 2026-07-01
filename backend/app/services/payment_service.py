"""
services/payment_service.py — Razorpay payment processing for Pepto orders.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import razorpay
from flask import current_app
from sqlalchemy import desc

from app.extensions import db
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.payment import Payment
from app.utils.exceptions import (
    NotFoundError, ValidationError, AuthorizationError, ConflictError
)

logger = logging.getLogger(__name__)

PLATFORM_FEE_PERCENT = 10.0
FULL_REFUND_HOURS = 1        # Full refund if cancelled within 1 hr of ordering
PARTIAL_REFUND_RATE = 0.50   # 50% refund otherwise


def _get_razorpay_client() -> razorpay.Client:
    key_id = current_app.config.get("RAZORPAY_KEY_ID", "")
    key_secret = current_app.config.get("RAZORPAY_KEY_SECRET", "")
    return razorpay.Client(auth=(key_id, key_secret))


class PaymentService:

    # ── Create Razorpay order (called before checkout) ────────────────────────

    def create_razorpay_order(self, customer_id: str, order_id: str) -> Dict:
        """Create a Razorpay order for an existing Pepto order.

        The Razorpay order ID is stored on the Pepto order so we can verify
        payment later.

        Returns:
            {razorpay_order_id, amount_paise, currency, key_id}
        """
        pepto_order = Order.query.filter_by(id=order_id, customer_id=customer_id).first()
        if not pepto_order:
            raise NotFoundError("Order not found")
        if pepto_order.payment_status == PaymentStatus.paid:
            raise ConflictError("This order has already been paid")

        amount_paise = int(float(pepto_order.total) * 100)  # Razorpay uses paise

        client = _get_razorpay_client()
        rz_order = client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": pepto_order.order_number,
            "notes": {
                "pepto_order_id": order_id,
                "customer_id": customer_id,
            },
        })

        # Store Razorpay order ID on the Pepto order
        pepto_order.razorpay_order_id = rz_order["id"]
        db.session.commit()

        logger.info("Razorpay order created: %s for Pepto order %s", rz_order["id"], order_id)
        return {
            "razorpay_order_id": rz_order["id"],
            "amount_paise": amount_paise,
            "amount_inr": float(pepto_order.total),
            "currency": "INR",
            "key_id": current_app.config.get("RAZORPAY_KEY_ID", ""),
            "order_number": pepto_order.order_number,
        }

    # ── Verify payment signature (called after Razorpay checkout success) ─────

    def verify_payment(self, customer_id: str, data: dict) -> Dict:
        """Verify Razorpay payment signature and mark order as paid.

        Razorpay generates an HMAC-SHA256 signature using:
            razorpay_order_id + "|" + razorpay_payment_id

        Args:
            data: {razorpay_order_id, razorpay_payment_id, razorpay_signature}
        """
        rz_order_id = data["razorpay_order_id"]
        rz_payment_id = data["razorpay_payment_id"]
        rz_signature = data["razorpay_signature"]

        # Verify signature
        key_secret = current_app.config.get("RAZORPAY_KEY_SECRET", "")
        body = f"{rz_order_id}|{rz_payment_id}"
        expected_sig = hmac.new(
            key_secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, rz_signature):
            raise ValidationError("Payment signature verification failed")

        # Find the Pepto order
        order = Order.query.filter_by(razorpay_order_id=rz_order_id).first()
        if not order:
            raise NotFoundError("Order not found for this Razorpay order")
        if str(order.customer_id) != customer_id:
            raise AuthorizationError("Access denied")

        # Fetch payment details from Razorpay to get method
        client = _get_razorpay_client()
        try:
            rz_payment = client.payment.fetch(rz_payment_id)
            method = rz_payment.get("method", "card")
        except Exception:
            method = "card"

        # Update order
        order.payment_status = PaymentStatus.paid
        order.razorpay_payment_id = rz_payment_id
        order.status = OrderStatus.confirmed
        order.confirmed_at = datetime.now(timezone.utc)

        # Create payment record
        platform_fee = round(float(order.total) * PLATFORM_FEE_PERCENT / 100, 2)
        store_earning = round(float(order.total) - platform_fee - float(order.delivery_fee), 2)

        payment = Payment(
            order_id=str(order.id),
            amount=float(order.total),
            currency="INR",
            razorpay_order_id=rz_order_id,
            razorpay_payment_id=rz_payment_id,
            razorpay_signature=rz_signature,
            method=method,
            status="captured",
            platform_fee=platform_fee,
            store_earning=store_earning,
            paid_at=datetime.now(timezone.utc),
        )
        db.session.add(payment)
        db.session.commit()

        # Notify store via WebSocket
        try:
            from app.sockets import notify_order_status
            notify_order_status(str(order.id), "confirmed")
        except Exception:
            pass

        logger.info("Payment verified: %s for order %s", rz_payment_id, order.order_number)
        return {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "payment_id": str(payment.id),
            "razorpay_payment_id": rz_payment_id,
            "amount": float(order.total),
            "status": "paid",
        }

    # ── Webhook handler ───────────────────────────────────────────────────────

    def handle_webhook(self, event_type: str, event: dict) -> None:
        """Handle Razorpay webhook events.

        Supported events:
            payment.captured  — backup capture confirmation
            payment.failed    — mark payment as failed
            refund.processed  — mark refund as completed
        """
        payload = event.get("payload", {})

        if event_type == "payment.captured":
            payment_entity = payload.get("payment", {}).get("entity", {})
            rz_order_id = payment_entity.get("order_id")
            if rz_order_id:
                order = Order.query.filter_by(razorpay_order_id=rz_order_id).first()
                if order and order.payment_status != PaymentStatus.paid:
                    order.payment_status = PaymentStatus.paid
                    order.status = OrderStatus.confirmed
                    db.session.commit()
                    logger.info("Webhook: payment captured for order %s", rz_order_id)

        elif event_type == "payment.failed":
            payment_entity = payload.get("payment", {}).get("entity", {})
            rz_order_id = payment_entity.get("order_id")
            if rz_order_id:
                order = Order.query.filter_by(razorpay_order_id=rz_order_id).first()
                if order:
                    order.payment_status = PaymentStatus.failed
                    db.session.commit()
                    logger.warning("Webhook: payment failed for order %s", rz_order_id)

        elif event_type == "refund.processed":
            refund_entity = payload.get("refund", {}).get("entity", {})
            rz_payment_id = refund_entity.get("payment_id")
            if rz_payment_id:
                payment = Payment.query.filter_by(razorpay_payment_id=rz_payment_id).first()
                if payment:
                    payment.status = "refunded"
                    payment.refund_id = refund_entity.get("id")
                    payment.refunded_amount = refund_entity.get("amount", 0) / 100
                    payment.refunded_at = datetime.now(timezone.utc)
                    db.session.commit()
                    logger.info("Webhook: refund processed for payment %s", rz_payment_id)

    # ── Refund ────────────────────────────────────────────────────────────────

    def refund_order(self, requester_id: str, order_id: str) -> Dict:
        """Issue a full or partial refund via Razorpay.

        Refund policy:
            - Full refund if cancelled within FULL_REFUND_HOURS of placing the order.
            - 50% refund otherwise (PARTIAL_REFUND_RATE).
        """
        order = Order.query.get(order_id)
        if not order:
            raise NotFoundError("Order not found")
        if str(order.customer_id) != requester_id:
            raise AuthorizationError("Access denied")
        if order.payment_status != PaymentStatus.paid:
            raise ConflictError("No payment to refund")
        if order.status not in {OrderStatus.cancelled, OrderStatus.refunded}:
            raise ConflictError("Order must be cancelled before refund")

        payment = Payment.query.filter_by(order_id=order_id).first()
        if not payment or not payment.razorpay_payment_id:
            raise NotFoundError("Payment record not found")
        if payment.refunded_amount and float(payment.refunded_amount) > 0:
            raise ConflictError("This order has already been refunded")

        # Determine refund amount
        hours_since_order = (
            datetime.now(timezone.utc) - order.created_at.replace(tzinfo=timezone.utc)
        ).total_seconds() / 3600

        if hours_since_order <= FULL_REFUND_HOURS:
            refund_amount = float(order.total)
        else:
            refund_amount = round(float(order.total) * PARTIAL_REFUND_RATE, 2)

        refund_paise = int(refund_amount * 100)

        client = _get_razorpay_client()
        try:
            refund = client.payment.refund(payment.razorpay_payment_id, {
                "amount": refund_paise,
                "notes": {"order_id": order_id, "reason": "Customer cancellation"},
            })
        except Exception as exc:
            logger.exception("Razorpay refund failed: %s", exc)
            raise ConflictError("Refund processing failed. Please try again.")

        # Update records
        payment.status = "refunded"
        payment.refund_id = refund.get("id")
        payment.refunded_amount = refund_amount
        payment.refunded_at = datetime.now(timezone.utc)
        order.status = OrderStatus.refunded
        order.payment_status = PaymentStatus.refunded
        db.session.commit()

        logger.info("Refund issued: ₹%.2f for order %s", refund_amount, order.order_number)
        return {
            "refund_id": refund.get("id"),
            "order_id": order_id,
            "order_number": order.order_number,
            "amount_refunded": refund_amount,
            "full_refund": hours_since_order <= FULL_REFUND_HOURS,
            "status": "refunded",
        }

    # ── History ───────────────────────────────────────────────────────────────

    def get_history(self, customer_id: str, page: int = 1) -> Dict:
        payments = (
            Payment.query
            .join(Order)
            .filter(Order.customer_id == customer_id)
            .order_by(desc(Payment.paid_at))
            .paginate(page=page, per_page=20, error_out=False)
        )
        return {
            "items": [
                {
                    "id": str(p.id),
                    "order_id": str(p.order_id),
                    "amount": float(p.amount),
                    "currency": p.currency,
                    "method": p.method,
                    "status": p.status,
                    "razorpay_payment_id": p.razorpay_payment_id,
                    "refunded_amount": float(p.refunded_amount) if p.refunded_amount else 0,
                    "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                }
                for p in payments.items
            ],
            "total": payments.total,
            "page": payments.page,
            "has_next": payments.has_next,
        }
