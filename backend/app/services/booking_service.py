"""
app/services/booking_service.py
Complete booking lifecycle management for Pepto marketplace.
Includes pessimistic locking, state machine validation, and Celery task dispatch.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, Dict, Any

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.booking import Booking
from app.models.service import Service
from app.models.provider import ProviderProfile, ProviderAvailability
from app.models.user import User
from app.utils.errors import (
    ValidationError,
    NotFoundError,
    ConflictError,
    ForbiddenError,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Status state machine — maps current_status → allowed next statuses
# ──────────────────────────────────────────────────────────────────────────────
VALID_TRANSITIONS: Dict[str, list] = {
    "pending":     ["confirmed", "cancelled"],
    "confirmed":   ["in_progress", "cancelled"],
    "in_progress": ["completed", "cancelled"],
    "completed":   ["refunded"],
    "cancelled":   [],
    "refunded":    [],
}

PLATFORM_FEE_RATE = 0.10  # 10%
PENDING_EXPIRY_HOURS = 2


class BookingService:
    """Manages the full booking lifecycle for Pepto."""

    # ──────────────────────────────────────────────────────────────────────
    # Availability check
    # ──────────────────────────────────────────────────────────────────────

    def check_availability(
        self,
        provider_id: str,
        service_id: str,
        booking_date: date,
        start_time: time,
    ) -> bool:
        """
        Check whether a provider is available for a given date/time.

        Steps:
          1. Verify the provider has an availability slot for that day of week.
          2. Ensure proposed start_time falls within that slot.
          3. Pessimistically lock and count concurrent confirmed bookings.
          4. Return True if under max_concurrent_bookings.

        Raises:
            NotFoundError: provider or service not found.
            ValidationError: outside availability window.
        """
        provider: Optional[ProviderProfile] = ProviderProfile.query.filter_by(
            id=provider_id, is_active=True
        ).first()
        if not provider:
            raise NotFoundError(f"Provider '{provider_id}' not found.")

        service: Optional[Service] = Service.query.filter_by(
            id=service_id, provider_id=provider_id, is_active=True
        ).first()
        if not service:
            raise NotFoundError(f"Service '{service_id}' not found for this provider.")

        day_of_week: int = booking_date.weekday()  # 0=Mon … 6=Sun

        avail: Optional[ProviderAvailability] = ProviderAvailability.query.filter_by(
            provider_id=provider_id, day_of_week=day_of_week
        ).first()
        if not avail:
            raise ValidationError(
                f"Provider is not available on {booking_date.strftime('%A')}."
            )

        # ── Check time within slot ────────────────────────────────────────
        duration = timedelta(minutes=service.duration_minutes)
        end_time = (
            datetime.combine(booking_date, start_time) + duration
        ).time()

        if start_time < avail.start_time or end_time > avail.end_time:
            raise ValidationError(
                f"Requested time {start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')} "
                f"is outside the provider's availability "
                f"{avail.start_time.strftime('%H:%M')}–{avail.end_time.strftime('%H:%M')}."
            )

        # ── Pessimistic lock: count concurrent confirmed bookings ──────────
        concurrent_count = (
            db.session.query(Booking)
            .with_for_update(skip_locked=True)
            .filter(
                Booking.provider_id == provider_id,
                Booking.booking_date == booking_date,
                Booking.status.in_(["confirmed", "in_progress"]),
                Booking.start_time < end_time,
                Booking.end_time > start_time,
            )
            .count()
        )

        max_concurrent = avail.max_concurrent_bookings or 1
        return concurrent_count < max_concurrent

    # ──────────────────────────────────────────────────────────────────────
    # Create booking
    # ──────────────────────────────────────────────────────────────────────

    def create_booking(self, customer_id: str, data: dict) -> Booking:
        """
        Create a new booking after availability check.

        Args:
            customer_id: ID of the customer placing the booking.
            data: {provider_id, service_id, booking_date (ISO str),
                   start_time (HH:MM), pet_id (optional), notes (optional)}

        Returns:
            Created Booking instance.

        Raises:
            ConflictError: time slot taken.
            ValidationError: invalid data or outside availability.
            NotFoundError: provider/service not found.
        """
        provider_id: str = data.get("provider_id", "")
        service_id: str = data.get("service_id", "")
        notes: str = data.get("notes", "")
        pet_id: Optional[str] = data.get("pet_id")

        # ── Parse date/time ───────────────────────────────────────────────
        try:
            booking_date = datetime.strptime(data["booking_date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            raise ValidationError("booking_date must be in YYYY-MM-DD format.")

        try:
            start_time = datetime.strptime(data["start_time"], "%H:%M").time()
        except (KeyError, ValueError):
            raise ValidationError("start_time must be in HH:MM format.")

        if booking_date < datetime.now(timezone.utc).date():
            raise ValidationError("Cannot create a booking in the past.")

        service: Optional[Service] = Service.query.filter_by(
            id=service_id, is_active=True
        ).first()
        if not service:
            raise NotFoundError(f"Service '{service_id}' not found.")

        # ── Check availability (includes pessimistic lock) ─────────────────
        try:
            available = self.check_availability(
                provider_id, service_id, booking_date, start_time
            )
        except (ValidationError, NotFoundError):
            raise
        except Exception as exc:
            logger.exception("Availability check failed")
            raise ConflictError("Could not verify availability. Please try again.") from exc

        if not available:
            raise ConflictError("This time slot is already booked. Please choose another.")

        # ── Calculate times and amounts ───────────────────────────────────
        duration = timedelta(minutes=service.duration_minutes)
        end_time = (datetime.combine(booking_date, start_time) + duration).time()

        total_amount = service.price
        platform_fee = round(total_amount * PLATFORM_FEE_RATE, 2)
        provider_earning = round(total_amount - platform_fee, 2)

        # ── Create booking record ─────────────────────────────────────────
        booking = Booking(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            provider_id=provider_id,
            service_id=service_id,
            pet_id=pet_id,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            total_amount=total_amount,
            platform_fee=platform_fee,
            provider_earning=provider_earning,
            status="pending",
            notes=notes,
        )

        try:
            db.session.add(booking)
            db.session.commit()
            logger.info(
                "Booking created: %s | customer=%s | provider=%s | date=%s %s",
                booking.id, customer_id, provider_id, booking_date, start_time,
            )
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("Failed to create booking")
            raise

        # ── Async notifications ───────────────────────────────────────────
        try:
            from app.tasks.email_tasks import (
                send_booking_confirmation_task,
                send_booking_request_to_provider_task,
            )
            send_booking_confirmation_task.apply_async(args=[booking.id])
            send_booking_request_to_provider_task.apply_async(args=[booking.id])
        except Exception:
            logger.exception("Failed to enqueue booking notification tasks for %s", booking.id)

        return booking

    # ──────────────────────────────────────────────────────────────────────
    # Update booking status
    # ──────────────────────────────────────────────────────────────────────

    def update_booking_status(
        self,
        booking_id: str,
        new_status: str,
        actor_id: str,
        reason: Optional[str] = None,
    ) -> Booking:
        """
        Validate state transition and update booking status.

        Args:
            booking_id: Booking ID to update.
            new_status: Target status string.
            actor_id: User ID performing the update (for auth checks).
            reason: Cancellation reason (required if new_status == 'cancelled').

        Returns:
            Updated Booking.

        Raises:
            NotFoundError, ForbiddenError, ValidationError.
        """
        booking: Optional[Booking] = Booking.query.get(booking_id)
        if not booking:
            raise NotFoundError(f"Booking '{booking_id}' not found.")

        current_status = booking.status
        allowed = VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise ValidationError(
                f"Cannot transition booking from '{current_status}' to '{new_status}'. "
                f"Allowed: {allowed}"
            )

        old_status = current_status
        try:
            booking.status = new_status

            if new_status == "cancelled":
                booking.cancelled_at = datetime.now(timezone.utc)
                booking.cancellation_reason = reason or "No reason provided."

            if new_status == "completed":
                booking.completed_at = datetime.now(timezone.utc)

            db.session.commit()
            logger.info(
                "Booking %s: %s → %s (actor=%s)", booking_id, old_status, new_status, actor_id
            )
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("Failed to update booking %s status", booking_id)
            raise

        # ── Post-transition async tasks ────────────────────────────────────
        try:
            from app.tasks.email_tasks import (
                send_status_update_task,
                send_review_request_task,
            )
            from app.tasks.booking_tasks import process_refund_task

            send_status_update_task.apply_async(args=[booking_id, old_status, new_status])

            if new_status == "completed":
                send_review_request_task.apply_async(args=[booking_id], countdown=3600)

            if new_status == "cancelled":
                # Trigger refund only if payment has succeeded
                if booking.payment and booking.payment.status == "succeeded":
                    process_refund_task.apply_async(args=[booking_id], countdown=5)

        except Exception:
            logger.exception("Post-status-update tasks failed for booking %s", booking_id)

        return booking

    # ──────────────────────────────────────────────────────────────────────
    # Query methods
    # ──────────────────────────────────────────────────────────────────────

    def get_customer_bookings(
        self,
        customer_id: str,
        status: Optional[str] = None,
        page: int = 1,
    ) -> dict:
        """Paginated list of bookings for a customer."""
        per_page = 10
        query = Booking.query.filter_by(customer_id=customer_id)
        if status:
            query = query.filter_by(status=status)
        query = query.order_by(Booking.created_at.desc())

        total = query.count()
        bookings = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "bookings": [self._serialize_booking(b) for b in bookings],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max((total + per_page - 1) // per_page, 1),
        }

    def get_provider_bookings(
        self,
        provider_id: str,
        status: Optional[str] = None,
        booking_date: Optional[date] = None,
        page: int = 1,
    ) -> dict:
        """Paginated list of bookings for a provider, with optional date filter."""
        per_page = 10
        query = Booking.query.filter_by(provider_id=provider_id)
        if status:
            query = query.filter_by(status=status)
        if booking_date:
            query = query.filter_by(booking_date=booking_date)
        query = query.order_by(Booking.booking_date.asc(), Booking.start_time.asc())

        total = query.count()
        bookings = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "bookings": [self._serialize_booking(b) for b in bookings],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max((total + per_page - 1) // per_page, 1),
        }

    def cancel_booking(self, booking_id: str, user_id: str, reason: str) -> Booking:
        """
        Cancel a booking. Ownership is verified: customer or provider may cancel.

        Raises:
            NotFoundError, ForbiddenError, ValidationError.
        """
        booking: Optional[Booking] = Booking.query.get(booking_id)
        if not booking:
            raise NotFoundError(f"Booking '{booking_id}' not found.")

        # ── Ownership check ───────────────────────────────────────────────
        is_customer = booking.customer_id == user_id
        is_provider = (
            booking.provider is not None
            and booking.provider.user_id == user_id
        )
        if not (is_customer or is_provider):
            raise ForbiddenError("You do not have permission to cancel this booking.")

        if booking.status in ("cancelled", "refunded", "completed"):
            raise ValidationError(
                f"Cannot cancel a booking with status '{booking.status}'."
            )

        return self.update_booking_status(booking_id, "cancelled", user_id, reason)

    # ──────────────────────────────────────────────────────────────────────
    # Serializer
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _serialize_booking(booking: Booking) -> dict:
        service = booking.service
        provider = booking.provider
        customer = booking.customer
        return {
            "id": booking.id,
            "status": booking.status,
            "booking_date": booking.booking_date.isoformat() if booking.booking_date else None,
            "start_time": booking.start_time.strftime("%H:%M") if booking.start_time else None,
            "end_time": booking.end_time.strftime("%H:%M") if booking.end_time else None,
            "total_amount": float(booking.total_amount) if booking.total_amount else None,
            "platform_fee": float(booking.platform_fee) if booking.platform_fee else None,
            "provider_earning": float(booking.provider_earning) if booking.provider_earning else None,
            "notes": booking.notes,
            "cancellation_reason": booking.cancellation_reason,
            "cancelled_at": booking.cancelled_at.isoformat() if booking.cancelled_at else None,
            "completed_at": booking.completed_at.isoformat() if booking.completed_at else None,
            "created_at": booking.created_at.isoformat() if booking.created_at else None,
            "service": {
                "id": service.id,
                "name": service.name,
                "category": service.category,
                "duration_minutes": service.duration_minutes,
            } if service else None,
            "provider": {
                "id": provider.id,
                "business_name": provider.business_name,
                "profile_photo": provider.profile_photo,
            } if provider else None,
            "customer": {
                "id": customer.id,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "email": customer.email,
            } if customer else None,
        }
