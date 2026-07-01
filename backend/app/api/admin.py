"""
Pepto Pet Services Marketplace
Admin Blueprint — /api/admin
Requires: authenticated user with role='admin'
"""

from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, jsonify, request, g
from sqlalchemy import func, desc, or_

from app.extensions import db
from app.models import (
    User,
    Provider,
    Booking,
    Review,
    Pet,
    Service,
    Payment,
)
from app.utils.decorators import admin_required
from app.utils.helpers import paginate_query

# ---------------------------------------------------------------------------
# Blueprint setup
# ---------------------------------------------------------------------------
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")



@admin_bp.route("/stats", methods=["GET"])
@admin_required
def get_platform_stats():
    """
    Return a high-level snapshot of platform health:
      - Total users / providers / pets
      - Booking counts by status
      - Revenue (total, MTD, last-30-days)
      - New signups in the last 7 days
      - Provider verification queue size
    """
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)
    mtd_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # ── Users ──────────────────────────────────────────────────────────────
    total_users = db.session.query(func.count(User.id)).scalar()
    active_users = (
        db.session.query(func.count(User.id))
        .filter(User.is_active == True)  # noqa: E712
        .scalar()
    )
    new_users_7d = (
        db.session.query(func.count(User.id))
        .filter(User.created_at >= seven_days_ago)
        .scalar()
    )

    # ── Providers ──────────────────────────────────────────────────────────
    total_providers = db.session.query(func.count(Provider.id)).scalar()
    verified_providers = (
        db.session.query(func.count(Provider.id))
        .filter(Provider.is_verified == True)  # noqa: E712
        .scalar()
    )
    pending_verification = (
        db.session.query(func.count(Provider.id))
        .filter(Provider.is_verified == False)  # noqa: E712
        .scalar()
    )

    # ── Pets ───────────────────────────────────────────────────────────────
    total_pets = db.session.query(func.count(Pet.id)).scalar()

    # ── Bookings ───────────────────────────────────────────────────────────
    booking_stats_rows = (
        db.session.query(Booking.status, func.count(Booking.id))
        .group_by(Booking.status)
        .all()
    )
    booking_stats = {row[0]: row[1] for row in booking_stats_rows}
    total_bookings = sum(booking_stats.values())

    # ── Revenue ────────────────────────────────────────────────────────────
    total_revenue = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.status == "captured")
        .scalar()
    )
    revenue_mtd = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.status == "captured",
            Payment.created_at >= mtd_start,
        )
        .scalar()
    )
    revenue_30d = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.status == "captured",
            Payment.created_at >= thirty_days_ago,
        )
        .scalar()
    )

    # ── Reviews ────────────────────────────────────────────────────────────
    total_reviews = db.session.query(func.count(Review.id)).scalar()
    avg_rating = (
        db.session.query(func.round(func.avg(Review.rating), 2)).scalar() or 0.0
    )

    return (
        jsonify(
            {
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "new_last_7_days": new_users_7d,
                },
                "providers": {
                    "total": total_providers,
                    "verified": verified_providers,
                    "pending_verification": pending_verification,
                },
                "pets": {"total": total_pets},
                "bookings": {
                    "total": total_bookings,
                    "by_status": booking_stats,
                },
                "revenue": {
                    "total_usd": float(total_revenue),
                    "month_to_date_usd": float(revenue_mtd),
                    "last_30_days_usd": float(revenue_30d),
                },
                "reviews": {
                    "total": total_reviews,
                    "average_rating": float(avg_rating),
                },
                "generated_at": now.isoformat(),
            }
        ),
        200,
    )


# ===========================================================================
# GET /api/admin/users
# Paginated user list with search & filter
# ===========================================================================
@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """
    Query params:
      page     (int, default 1)
      per_page (int, default 20, max 100)
      search   (str) — searches email, first_name, last_name
      role     (str) — filter by role: user | provider | admin
      is_active (bool) — filter by account status
      sort     (str)  — created_at | email (default: created_at)
      order    (str)  — asc | desc          (default: desc)
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    search = request.args.get("search", "").strip()
    role_filter = request.args.get("role")
    is_active_filter = request.args.get("is_active")
    sort_field = request.args.get("sort", "created_at")
    order = request.args.get("order", "desc")

    query = db.session.query(User)

    # ── Filters ─────────────────────────────────────────────────────────────
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                User.email.ilike(like),
                User.first_name.ilike(like),
                User.last_name.ilike(like),
            )
        )

    if role_filter in ("user", "provider", "admin"):
        query = query.filter(User.role == role_filter)

    if is_active_filter is not None:
        active_bool = is_active_filter.lower() in ("true", "1", "yes")
        query = query.filter(User.is_active == active_bool)

    # ── Sorting ─────────────────────────────────────────────────────────────
    sort_column = getattr(User, sort_field, User.created_at)
    query = query.order_by(desc(sort_column) if order == "desc" else sort_column)

    # ── Pagination ──────────────────────────────────────────────────────────
    pagination = paginate_query(query, page, per_page)

    return (
        jsonify(
            {
                "users": [u.to_admin_dict() for u in pagination.items],
                "pagination": {
                    "page": pagination.page,
                    "per_page": pagination.per_page,
                    "total": pagination.total,
                    "pages": pagination.pages,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev,
                },
            }
        ),
        200,
    )


# ===========================================================================
# PUT /api/admin/users/<id>/status
# Activate or deactivate a user account
# ===========================================================================
@admin_bp.route("/users/<int:user_id>/status", methods=["PUT"])
@admin_required
def update_user_status(user_id: int):
    """
    Body: { "is_active": true|false, "reason": "optional note" }

    Prevents an admin from deactivating their own account.
    Logs the action to the audit trail.
    """
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "not_found", "message": "User not found."}), 404

    # Prevent self-deactivation
    if user.id == g.current_user.id:
        return (
            jsonify(
                {
                    "error": "forbidden",
                    "message": "You cannot change your own account status.",
                }
            ),
            403,
        )

    data = request.get_json(silent=True) or {}
    new_status = data.get("is_active")
    reason = data.get("reason", "")

    if new_status is None or not isinstance(new_status, bool):
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "message": "`is_active` (boolean) is required.",
                }
            ),
            422,
        )

    old_status = user.is_active
    user.is_active = new_status
    user.updated_at = datetime.utcnow()

    # Persist
    db.session.commit()

    # Audit log (best-effort)
    _log_admin_action(
        action="user_status_change",
        target_type="user",
        target_id=user_id,
        details={
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason,
        },
    )

    action_word = "activated" if new_status else "deactivated"
    return (
        jsonify(
            {
                "message": f"User {user.email} has been {action_word}.",
                "user": user.to_admin_dict(),
            }
        ),
        200,
    )


# ===========================================================================
# PUT /api/admin/providers/<id>/verify
# Toggle provider business verification
# ===========================================================================
@admin_bp.route("/providers/<int:provider_id>/verify", methods=["PUT"])
@admin_required
def verify_provider(provider_id: int):
    """
    Body: { "is_verified": true|false, "notes": "optional admin note" }

    When a provider is verified:
      - is_verified is set to True
      - verified_at timestamp is set
      - verified_by is set to the admin's user ID
    Sends an email notification via Celery (non-blocking).
    """
    provider = db.session.get(Provider, provider_id)
    if not provider:
        return (
            jsonify({"error": "not_found", "message": "Provider not found."}),
            404,
        )

    data = request.get_json(silent=True) or {}
    is_verified = data.get("is_verified")
    notes = data.get("notes", "")

    if is_verified is None or not isinstance(is_verified, bool):
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "message": "`is_verified` (boolean) is required.",
                }
            ),
            422,
        )

    provider.is_verified = is_verified
    provider.verification_notes = notes

    if is_verified:
        provider.verified_at = datetime.utcnow()
        provider.verified_by_id = g.current_user.id
    else:
        provider.verified_at = None
        provider.verified_by_id = None

    db.session.commit()

    # Non-blocking email notification via Celery
    try:
        from app.tasks.email_tasks import send_provider_verification_email

        send_provider_verification_email.delay(provider.id, is_verified, notes)
    except Exception:
        pass  # Email failure should not break the API response

    _log_admin_action(
        action="provider_verification",
        target_type="provider",
        target_id=provider_id,
        details={"is_verified": is_verified, "notes": notes},
    )

    status_word = "verified" if is_verified else "unverified"
    return (
        jsonify(
            {
                "message": f"Provider has been {status_word}.",
                "provider": provider.to_admin_dict(),
            }
        ),
        200,
    )


# ===========================================================================
# GET /api/admin/bookings
# All bookings with filtering and pagination
# ===========================================================================
@admin_bp.route("/bookings", methods=["GET"])
@admin_required
def list_bookings():
    """
    Query params:
      page          (int)
      per_page      (int, max 100)
      status        (str)  — pending|confirmed|in_progress|completed|cancelled
      provider_id   (int)
      user_id       (int)
      date_from     (ISO date string)
      date_to       (ISO date string)
      sort          (str)  — created_at|scheduled_at|total_price
      order         (str)  — asc|desc
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    status_filter = request.args.get("status")
    provider_id = request.args.get("provider_id", type=int)
    user_id = request.args.get("user_id", type=int)
    date_from_str = request.args.get("date_from")
    date_to_str = request.args.get("date_to")
    sort_field = request.args.get("sort", "created_at")
    order = request.args.get("order", "desc")

    VALID_STATUSES = {
        "pending",
        "confirmed",
        "in_progress",
        "completed",
        "cancelled",
        "refunded",
    }

    query = db.session.query(Booking)

    if status_filter and status_filter in VALID_STATUSES:
        query = query.filter(Booking.status == status_filter)

    if provider_id:
        query = query.filter(Booking.provider_id == provider_id)

    if user_id:
        query = query.filter(Booking.user_id == user_id)

    if date_from_str:
        try:
            date_from = datetime.fromisoformat(date_from_str)
            query = query.filter(Booking.scheduled_at >= date_from)
        except ValueError:
            pass

    if date_to_str:
        try:
            date_to = datetime.fromisoformat(date_to_str)
            query = query.filter(Booking.scheduled_at <= date_to)
        except ValueError:
            pass

    sort_column = getattr(Booking, sort_field, Booking.created_at)
    query = query.order_by(desc(sort_column) if order == "desc" else sort_column)

    pagination = paginate_query(query, page, per_page)

    return (
        jsonify(
            {
                "bookings": [b.to_admin_dict() for b in pagination.items],
                "pagination": {
                    "page": pagination.page,
                    "per_page": pagination.per_page,
                    "total": pagination.total,
                    "pages": pagination.pages,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev,
                },
            }
        ),
        200,
    )


# ===========================================================================
# DELETE /api/admin/reviews/<id>
# Remove an inappropriate or spam review
# ===========================================================================
@admin_bp.route("/reviews/<int:review_id>", methods=["DELETE"])
@admin_required
def delete_review(review_id: int):
    """
    Soft-deletes a review (sets is_deleted=True and records the reason).
    Body: { "reason": "Spam / inappropriate content / policy violation" }

    Hard-delete is intentionally avoided to preserve audit trails.
    """
    review = db.session.get(Review, review_id)
    if not review:
        return (
            jsonify({"error": "not_found", "message": "Review not found."}),
            404,
        )

    if review.is_deleted:
        return (
            jsonify(
                {"error": "already_deleted", "message": "Review has already been removed."}
            ),
            409,
        )

    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "Removed by administrator").strip()

    if not reason:
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "message": "`reason` is required when deleting a review.",
                }
            ),
            422,
        )

    # Soft delete
    review.is_deleted = True
    review.deleted_at = datetime.utcnow()
    review.deleted_by_id = g.current_user.id
    review.deletion_reason = reason

    # Recalculate provider average rating (exclude deleted reviews)
    provider = db.session.get(Provider, review.provider_id)
    if provider:
        new_avg = (
            db.session.query(func.avg(Review.rating))
            .filter(
                Review.provider_id == review.provider_id,
                Review.is_deleted == False,  # noqa: E712
            )
            .scalar()
        )
        provider.average_rating = round(float(new_avg), 2) if new_avg else 0.0
        provider.review_count = (
            db.session.query(func.count(Review.id))
            .filter(
                Review.provider_id == review.provider_id,
                Review.is_deleted == False,  # noqa: E712
            )
            .scalar()
        )

    db.session.commit()

    _log_admin_action(
        action="review_deleted",
        target_type="review",
        target_id=review_id,
        details={"reason": reason},
    )

    return (
        jsonify(
            {
                "message": "Review removed successfully.",
                "review_id": review_id,
                "reason": reason,
            }
        ),
        200,
    )


# ---------------------------------------------------------------------------
# Private helper: write to admin audit log
# ---------------------------------------------------------------------------
def _log_admin_action(
    action: str,
    target_type: str,
    target_id: int,
    details: dict | None = None,
) -> None:
    """
    Best-effort audit log. Failures are silently swallowed so that admin
    actions are never blocked by a logging error.
    """
    try:
        from app.models import AdminAuditLog  # local import to avoid circular dep

        log_entry = AdminAuditLog(
            admin_id=g.current_user.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", ""),
            created_at=datetime.utcnow(),
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
