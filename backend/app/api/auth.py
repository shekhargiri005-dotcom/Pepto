"""
app/api/auth.py
Authentication Blueprint for Pepto marketplace.
Handles registration, login, token management, and profile operations.
"""

from __future__ import annotations

import logging
from flask import Blueprint, request, current_app

from app.services.auth_service import AuthService
from app.utils.decorators import require_auth
from app.utils.helpers import success_response, error_response
from app.utils.validators import (
    validate_register_input,
    validate_login_input,
    validate_update_profile_input,
)
from app.utils.exceptions import (
    ValidationError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
)
from app.extensions import limiter

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
_auth_svc = AuthService()


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/register
# ──────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per hour")
def register():
    """Register a new user account."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        validated = validate_register_input(data)
        user = _auth_svc.register_user(validated)
        return success_response(
            data={
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
            },
            message="Registration successful. Please check your email to verify your account.",
            status_code=201,
        )
    except ConflictError as exc:
        return error_response(str(exc), status_code=409)
    except ValidationError as exc:
        return error_response(str(exc), status_code=422)
    except Exception:
        current_app.logger.exception("Unexpected error in register()")
        return error_response("An unexpected error occurred.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/login
# ──────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per hour")
def login():
    """Authenticate user and return JWT tokens."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        email, password = validate_login_input(data)
        result = _auth_svc.login_user(email, password)
        return success_response(data=result, message="Login successful.")
    except AuthenticationError as exc:
        status = getattr(exc, "status_code", 401)
        return error_response(str(exc), status_code=status)
    except ValidationError as exc:
        return error_response(str(exc), status_code=422)
    except Exception:
        current_app.logger.exception("Unexpected error in login()")
        return error_response("An unexpected error occurred.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/refresh
# ──────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/refresh", methods=["POST"])
def refresh_token():
    """Exchange a refresh token for a new access token."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        refresh_tok = data.get("refresh_token", "").strip()
        if not refresh_tok:
            return error_response("refresh_token is required.", status_code=400)
        new_access = _auth_svc.refresh_access_token(refresh_tok)
        return success_response(
            data={"access_token": new_access},
            message="Token refreshed successfully.",
        )
    except AuthenticationError as exc:
        return error_response(str(exc), status_code=401)
    except Exception:
        current_app.logger.exception("Unexpected error in refresh_token()")
        return error_response("An unexpected error occurred.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/logout
# ──────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    """Blacklist the current access token (logout)."""
    try:
        token = getattr(request, "current_token", None)
        user = request.current_user
        _auth_svc.logout_user(token, user.id)
        return success_response(message="Logged out successfully.")
    except Exception:
        current_app.logger.exception("Unexpected error in logout()")
        return error_response("Logout failed.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/auth/verify-email/<token>
# ──────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/verify-email/<string:token>", methods=["GET"])
def verify_email(token: str):
    """Verify a user's email address using the token from the verification link."""
    try:
        _auth_svc.verify_email(token)
        return success_response(message="Email verified successfully. You can now log in.")
    except AuthenticationError as exc:
        return error_response(str(exc), status_code=400)
    except NotFoundError as exc:
        return error_response(str(exc), status_code=404)
    except Exception:
        current_app.logger.exception("Unexpected error in verify_email()")
        return error_response("Email verification failed.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/forgot-password
# ──────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per hour")
def forgot_password():
    """Send a password reset link to the given email address."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        if not email:
            return error_response("Email is required.", status_code=400)

        from app.models.user import User
        from app.services.notification_service import NotificationService

        user = User.query.filter_by(email=email).first()
        # Always return success to prevent email enumeration
        if user and user.is_active:
            token = _auth_svc.generate_password_reset_token(user)
            svc = NotificationService()
            svc.send_password_reset(user, token)

        return success_response(
            message="If that email is registered, you will receive a reset link shortly."
        )
    except Exception:
        current_app.logger.exception("Unexpected error in forgot_password()")
        return error_response("An unexpected error occurred.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/reset-password
# ──────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit("5 per hour")
def reset_password():
    """Reset password using a valid reset token."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        token = (data.get("token") or "").strip()
        new_password = data.get("new_password") or data.get("password") or ""

        if not token:
            return error_response("Reset token is required.", status_code=400)
        if not new_password:
            return error_response("New password is required.", status_code=400)

        _auth_svc.reset_password(token, new_password)
        return success_response(
            message="Password reset successfully. Please log in with your new password."
        )
    except AuthenticationError as exc:
        return error_response(str(exc), status_code=400)
    except ValidationError as exc:
        return error_response(str(exc), status_code=422)
    except NotFoundError as exc:
        return error_response(str(exc), status_code=404)
    except Exception:
        current_app.logger.exception("Unexpected error in reset_password()")
        return error_response("Password reset failed.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/auth/me
# ──────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@require_auth
def get_current_user():
    """Return the authenticated user's profile."""
    try:
        user = request.current_user
        return success_response(
            data={
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "role": user.role,
                "is_email_verified": user.is_email_verified,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
            }
        )
    except Exception:
        current_app.logger.exception("Unexpected error in get_current_user()")
        return error_response("Failed to retrieve user.", status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# PUT /api/auth/me
# ──────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["PUT"])
@require_auth
def update_profile():
    """Update the authenticated user's profile details."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        validated = validate_update_profile_input(data)
        user = request.current_user

        from app.extensions import db

        if "first_name" in validated:
            user.first_name = validated["first_name"]
        if "last_name" in validated:
            user.last_name = validated["last_name"]
        if "phone" in validated:
            user.phone = validated["phone"]

        db.session.commit()

        return success_response(
            data={
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "role": user.role,
            },
            message="Profile updated successfully.",
        )
    except ValidationError as exc:
        return error_response(str(exc), status_code=422)
    except Exception:
        from app.extensions import db
        db.session.rollback()
        current_app.logger.exception("Unexpected error in update_profile()")
        return error_response("Failed to update profile.", status_code=500)
