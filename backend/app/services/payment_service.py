"""
app/services/payment_service.py
Stripe payment integration for Pepto marketplace.
Handles PaymentIntents, webhooks, refunds, and earnings reporting.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

import stripe
from flask import current_app
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.provider import ProviderProfile
from app.models.user import User
from app.utils.errors import (
    ValidationError,
    NotFoundError,
    ConflictError,
    ForbiddenError,
    PaymentError,
)

logger = logging.getLogger(__name__)

PLATFORM_FEE_RATE = 0.10
FULL_REFUND_HOURS = 24       # full refund if >24h before booking
PARTIAL_REFUND_RATE = 0.50   # 50% refund if <24h before booking


def _init_stripe() -> None:
    """Configure Stripe API key from app config."""
    key = current_app.config.get("STRIPE_SECRET_KEY", "")
    if not key:
        raise PaymentError("Stripe secret key is not configured.")
    stripe.api_key = key


class PaymentService:
    """
    Manages Stripe payments, webhooks, refunds, and provider earnings.
    All amounts stored in INR (₹). Stripe receives paise (×100).
    """

    # ──────────────────────────────────────────────────────────────────────
    # Create Payment Intent
    # ──────────────────────────────────────────────────────────────────────

    def create_payment_intent(self, booking_id: str, customer_id: str) -> dict:
        """
        Create a Stripe PaymentIntent and a local Payment record.

        Args:
            booking_id: Booking that is being paid for.
            customer_id: Customer initiating the payment (ownership check).

        Returns:
            {client_secret, payment_intent_id, amount, currency}

        Raises:
            NotFoundError, ForbiddenError, ConflictError, PaymentError.
        """
        _init_stripe()

        booking: Optional[Booking] = Booking.query.get(booking_id)
        if not booking:
            raise NotFoundError(f"Booking '{booking_id}' not found.")

        if booking.customer_id != customer_id:
            raise ForbiddenError("This booking does not belong to you.")

        if booking.status != "confirmed":
            raise ConflictError(
                f"Payment can only be initiated for confirmed bookings "
                f"(current status: '{booking.status}')."
            )

        # Check for duplicate pending payment
        existing_payment: Optional[Payment] = Payment.query.filter_by(
            booking_id=booking_id, status="pending"
        ).first()
        if existing_payment:
            return {
                "client_secret": existing_payment.stripe_client_secret,
                "payment_intent_id": existing_payment.stripe_payment_intent_id,
                "amount": float(booking.total_amount),
                "currency": "inr",
            }

        amount_paise = int(float(booking.total_amount) * 100)

        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_paise,
                currency="inr",
                payment_method_types=["card"],
                metadata={
                    "booking_id": booking_id,
                    "customer_id": customer_id,
                    "provider_id": booking.provider_id or "",
                },
                description=f"Pepto booking {booking_id[:8].upper()}",
            )
        except stripe.error.StripeError as exc:
            logger.exception("Stripe PaymentIntent creation failed for booking %s", booking_id)
            raise PaymentError(f"Payment initiation failed: {exc.user_message}") from exc

        payment = Payment(
            id=str(uuid.uuid4()),
            booking_id=booking_id,
            customer_id=customer_id,
            provider_id=booking.provider_id,
            stripe_payment_intent_id=intent.id,
            stripe_client_secret=intent.client_secret,
            amount=booking.total_amount,
            platform_fee=booking.platform_fee,
            provider_earning=booking.provider_earning,
            currency="inr",
            status="pending",
        )

        try:
            db.session.add(payment)
            db.session.commit()
            logger.info(
                "Payment intent created: %s (₹%.2f) for booking %s",
                intent.id, booking.total_amount, booking_id,
            )
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("Failed to save Payment record for booking %s", booking_id)
            raise

        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id,
            "amount": float(booking.total_amount),
            "currency": "inr",
        }

    # ──────────────────────────────────────────────────────────────────────
    # Stripe Webhook handler
    # ──────────────────────────────────────────────────────────────────────

    def handle_webhook(self, payload: bytes, sig_header: str) -> None:
        """
        Verify Stripe webhook signature and process events.

        Supported events:
          • payment_intent.succeeded
          • payment_intent.payment_failed
          • charge.refunded

        Raises:
            PaymentError: signature invalid or event construction fails.
        """
        _init_stripe()
        webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET", "")
        if not webhook_secret:
            raise PaymentError("Stripe webhook secret is not configured.")

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except stripe.error.SignatureVerificationError as exc:
            raise PaymentError(f"Invalid Stripe webhook signature: {exc}") from exc
        except ValueError as exc:
            raise PaymentError(f"Invalid webhook payload: {exc}") from exc

        event_type: str = event["type"]
        event_data = event["data"]["object"]

        logger.info("Stripe webhook received: %s | id=%s", event_type, event.get("id"))

        if event_type == "payment_intent.succeeded":
            self._handle_payment_succeeded(event_data)
        elif event_type == "payment_intent.payment_failed":
            self._handle_payment_failed(event_data)
        elif event_type == "charge.refunded":
            self._handle_charge_refunded(event_data)
        else:
            logger.debug("Unhandled Stripe event type: %s", event_type)

    def _handle_payment_succeeded(self, intent: dict) -> None:
        intent_id: str = intent.get("id", "")
        payment: Optional[Payment] = Payment.query.filter_by(
            stripe_payment_intent_id=intent_id
        ).first()
        if not payment:
            logger.warning("PaymentIntent succeeded but no Payment found: %s", intent_id)
            return

        try:
            payment.status = "succeeded"
            payment.paid_at = datetime.now(timezone.utc)
            payment.stripe_charge_id = intent.get("latest_charge")

            # Update associated booking to 'confirmed' if still pending
            booking: Optional[Booking] = Booking.query.get(payment.booking_id)
            if booking and booking.status == "confirmed":
                pass  # Already confirmed — no change needed
            elif booking and booking.status == "pending":
                booking.status = "confirmed"

            db.session.commit()
            logger.info("Payment succeeded: %s | booking=%s", intent_id, payment.booking_id)
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("Failed to update payment on success: %s", intent_id)

    def _handle_payment_failed(self, intent: dict) -> None:
        intent_id: str = intent.get("id", "")
        payment: Optional[Payment] = Payment.query.filter_by(
            stripe_payment_intent_id=intent_id
        ).first()
        if not payment:
            logger.warning("PaymentIntent failed but no Payment found: %s", intent_id)
            return

        failure_msg: str = (
            intent.get("last_payment_error", {}).get("message", "Unknown error")
        )
        try:
            payment.status = "failed"
            payment.failure_reason = failure_msg
            db.session.commit()
            logger.warning("Payment failed: %s | reason: %s", intent_id, failure_msg)
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("Failed to update payment on failure: %s", intent_id)

        # Notify customer
        try:
            from app.tasks.email_tasks import send_payment_failed_task
            send_payment_failed_task.apply_async(args=[payment.booking_id])
        except Exception:
            logger.exception("Failed to enqueue payment failed notification")

    def _handle_charge_refunded(self, charge: dict) -> None:
        charge_id: str = charge.get("id", "")
        amount_refunded_paise: int = charge.get("amount_refunded", 0)
        amount_refunded = round(amount_refunded_paise / 100, 2)

        payment: Optional[Payment] = Payment.query.filter_by(
            stripe_charge_id=charge_id
        ).first()
        if not payment:
            logger.warning("charge.refunded but no Payment found for charge %s", charge_id)
            return

        try:
            payment.refunded_amount = amount_refunded
            payment.refunded_at = datetime.now(timezone.utc)
            payment.status = "refunded"

            booking: Optional[Booking] = Booking.query.get(payment.booking_id)
            if booking:
                booking.status = "refunded"

            db.session.commit()
            logger.info(
                "Refund processed: ₹%.2f for booking %s", amount_refunded, payment.booking_id
            )
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("Failed to update payment on refund for charge %s", charge_id)

    # ──────────────────────────────────────────────────────────────────────
    # Refund
    # ──────────────────────────────────────────────────────────────────────

    def create_refund(self, booking_id: str, requester_id: str) -> dict:
        """
        Issue a Stripe refund. Full refund >24h before booking, 50% otherwise.

        Args:
            booking_id: Booking to refund.
            requester_id: User requesting the refund (ownership check).

        Returns:
            {refund_id, amount_refunded, booking_id, status}

        Raises:
            NotFoundError, ForbiddenError, ValidationError, PaymentError.
        """
        _init_stripe()

        booking: Optional[Booking] = Booking.query.get(booking_id)
        if not booking:
            raise NotFoundError(f"Booking '{booking_id}' not found.")

        if booking.customer_id != requester_id:
            raise ForbiddenError("You do not have permission to refund this booking.")

        payment: Optional[Payment] = Payment.query.filter_by(
            booking_id=booking_id, status="succeeded"
        ).first()
        if not payment:
            raise ValidationError("No successful payment found for this booking.")

        if payment.status == "refunded":
            raise ConflictError("This booking has already been refunded.")

        # ── Calculate refund amount ───────────────────────────────────────
        if booking.booking_date:
            booking_dt = datetime.combine(booking.booking_date, booking.start_time or datetime.min.time())
            booking_dt = booking_dt.replace(tzinfo=timezone.utc)
            hours_until = (booking_dt - datetime.now(timezone.utc)).total_seconds() / 3600
            if hours_until > FULL_REFUND_HOURS:
                refund_amount = float(booking.total_amount)
            else:
                refund_amount = round(float(booking.total_amount) * PARTIAL_REFUND_RATE, 2)
        else:
            refund_amount = float(booking.total_amount)

        refund_amount_paise = int(refund_amount * 100)

        # ── Issue Stripe refund ───────────────────────────────────────────
        try:
            refund = stripe.Refund.create(
                charge=payment.stripe_charge_id,
                amount=refund_amount_paise,
                metadata={"booking_id": booking_id, "requester_id": requester_id},
            )
        except stripe.error.StripeError as exc:
            logger.exception("Stripe refund failed for booking %s", booking_id)
            raise PaymentError(f"Refund failed: {exc.user_message}") from exc

        # ── Update records ────────────────────────────────────────────────
        try:
            payment.status = "refunded"
            payment.refunded_amount = refund_amount
            payment.refunded_at = datetime.now(timezone.utc)
            payment.stripe_refund_id = refund.id

            booking.status = "refunded"
            booking.cancellation_reason = f"Refund processed (₹{refund_amount:.2f})"

            db.session.commit()
            logger.info(
                "Refund created: %s | ₹%.2f for booking %s",
                refund.id, refund_amount, booking_id,
            )
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("Failed to update records after refund for booking %s", booking_id)
            raise

        return {
            "refund_id": refund.id,
            "amount_refunded": refund_amount,
            "booking_id": booking_id,
            "status": "refunded",
        }

    # ──────────────────────────────────────────────────────────────────────
    # Provider Earnings
    # ──────────────────────────────────────────────────────────────────────

    def get_provider_earnings(
        self,
        provider_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """
        Aggregate provider earnings from completed bookings.

        Returns:
            {total_earnings, total_bookings, avg_booking_value, by_month: [...]}
        """
        query = (
            db.session.query(Payment)
            .join(Booking, Payment.booking_id == Booking.id)
            .filter(
                Payment.provider_id == provider_id,
                Payment.status == "succeeded",
                Booking.status == "completed",
            )
        )

        if start_date:
            query = query.filter(Payment.paid_at >= start_date)
        if end_date:
            query = query.filter(Payment.paid_at <= end_date)

        payments: List[Payment] = query.all()

        total_earnings = sum(float(p.provider_earning or 0) for p in payments)
        total_bookings = len(payments)
        avg_booking_value = (
            round(total_earnings / total_bookings, 2) if total_bookings > 0 else 0.0
        )

        # ── Monthly breakdown ─────────────────────────────────────────────
        monthly: Dict[str, Dict[str, Any]] = {}
        for p in payments:
            if p.paid_at:
                month_key = p.paid_at.strftime("%Y-%m")
                if month_key not in monthly:
                    monthly[month_key] = {"month": month_key, "earnings": 0.0, "bookings": 0}
                monthly[month_key]["earnings"] += float(p.provider_earning or 0)
                monthly[month_key]["bookings"] += 1

        by_month = sorted(monthly.values(), key=lambda x: x["month"])
        for m in by_month:
            m["earnings"] = round(m["earnings"], 2)

        return {
            "total_earnings": round(total_earnings, 2),
            "total_bookings": total_bookings,
            "avg_booking_value": avg_booking_value,
            "by_month": by_month,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Payment history
    # ──────────────────────────────────────────────────────────────────────

    def get_payment_history(self, customer_id: str, page: int = 1) -> dict:
        """Paginated payment history for a customer."""
        per_page = 10
        query = (
            Payment.query.filter_by(customer_id=customer_id)
            .order_by(Payment.created_at.desc())
        )
        total = query.count()
        payments = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "payments": [self._serialize_payment(p) for p in payments],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max((total + per_page - 1) // per_page, 1),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Serializer
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _serialize_payment(payment: Payment) -> dict:
        return {
            "id": payment.id,
            "booking_id": payment.booking_id,
            "stripe_payment_intent_id": payment.stripe_payment_intent_id,
            "amount": float(payment.amount) if payment.amount else None,
            "platform_fee": float(payment.platform_fee) if payment.platform_fee else None,
            "provider_earning": float(payment.provider_earning) if payment.provider_earning else None,
            "currency": payment.currency,
            "status": payment.status,
            "refunded_amount": float(payment.refunded_amount) if payment.refunded_amount else None,
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
            "refunded_at": payment.refunded_at.isoformat() if payment.refunded_at else None,
            "created_at": payment.created_at.isoformat() if payment.created_at else None,
        }
