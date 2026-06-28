"""
app/services/auth_service.py
Complete authentication service for Pepto marketplace.
Uses PyJWT directly for custom claims, bcrypt for password hashing,
and Redis for token blacklisting.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import bcrypt
from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.extensions import db, redis_client
from app.models.user import User
from app.services.notification_service import NotificationService
from app.utils.errors import (
    ValidationError,
    AuthenticationError,
    NotFoundError,
    ConflictError,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
ACCESS_TOKEN_EXPIRY_SECONDS: int = 3600          # 1 hour
REFRESH_TOKEN_EXPIRY_SECONDS: int = 7 * 24 * 3600  # 7 days
EMAIL_VERIFY_TOKEN_EXPIRY_SECONDS: int = 24 * 3600  # 24 hours
PASSWORD_RESET_TOKEN_EXPIRY_SECONDS: int = 3600     # 1 hour
BLACKLIST_KEY_PREFIX: str = "token_blacklist:"


class AuthService:
    """Handles all authentication flows: register, login, token management."""

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def register_user(self, data: dict) -> User:
        """
        Validate uniqueness, hash password, create User, send verification email.

        Args:
            data: dict with keys: email, password, first_name, last_name,
                  phone (optional), role (optional, default 'customer')

        Returns:
            Newly created (unverified) User instance.

        Raises:
            ConflictError: email already registered.
            ValidationError: required fields missing or invalid.
        """
        email: str = (data.get("email") or "").strip().lower()
        password: str = data.get("password") or ""
        first_name: str = (data.get("first_name") or "").strip()
        last_name: str = (data.get("last_name") or "").strip()
        phone: Optional[str] = data.get("phone")
        role: str = data.get("role", "customer")

        # ── Basic validation ──────────────────────────────────────────────
        if not email:
            raise ValidationError("Email is required.")
        if not password or len(password) < 8:
            raise ValidationError(
                "Password must be at least 8 characters long."
            )
        if not first_name or not last_name:
            raise ValidationError("First name and last name are required.")
        if role not in ("customer", "provider", "admin"):
            raise ValidationError("Invalid role specified.")

        # ── Uniqueness check ──────────────────────────────────────────────
        existing = User.query.filter_by(email=email).first()
        if existing:
            raise ConflictError(f"Email '{email}' is already registered.")

        # ── Hash password ─────────────────────────────────────────────────
        password_hash = self._hash_password(password)

        # ── Create user ───────────────────────────────────────────────────
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=role,
            is_active=True,
            is_email_verified=False,
        )

        try:
            db.session.add(user)
            db.session.commit()
            logger.info("Registered new user: %s (role=%s)", email, role)
        except IntegrityError:
            db.session.rollback()
            raise ConflictError(f"Email '{email}' is already registered.")
        except Exception:
            db.session.rollback()
            logger.exception("Failed to create user: %s", email)
            raise

        # ── Send verification email (best-effort) ─────────────────────────
        try:
            verify_token = self._generate_email_verify_token(user.id)
            notification_svc = NotificationService()
            notification_svc.send_verification_email(user, verify_token)
        except Exception:
            logger.exception(
                "Failed to send verification email to %s (user still created)", email
            )

        return user

    # ──────────────────────────────────────────────────────────────────────

    def login_user(self, email: str, password: str) -> dict:
        """
        Verify credentials, check account status, update last_login.

        Returns:
            {access_token, refresh_token, user}

        Raises:
            AuthenticationError: wrong credentials.
            AuthenticationError (403): account inactive or email not verified.
        """
        email = (email or "").strip().lower()

        user: Optional[User] = User.query.filter_by(email=email).first()
        if not user or not self._verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationError(
                "Account is deactivated. Contact support.", status_code=403
            )

        if not user.is_email_verified:
            raise AuthenticationError(
                "Please verify your email address before logging in.", status_code=403
            )

        # ── Update last_login ─────────────────────────────────────────────
        try:
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Failed to update last_login for user %s", user.id)

        tokens = self.generate_tokens(user.id, user.role)
        logger.info("User logged in: %s", email)

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": self._serialize_user(user),
        }

    # ──────────────────────────────────────────────────────────────────────

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Validate refresh token (check Redis blacklist), return new access_token.

        Raises:
            AuthenticationError: token invalid, expired, or blacklisted.
        """
        payload = self._decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type.")

        jti: str = payload.get("jti", "")
        if self._is_blacklisted(jti):
            raise AuthenticationError("Token has been revoked.")

        user_id: str = payload["sub"]
        role: str = payload.get("role", "customer")

        new_access_token = self._create_access_token(user_id, role)
        logger.debug("Refreshed access token for user %s", user_id)
        return new_access_token

    # ──────────────────────────────────────────────────────────────────────

    def logout_user(self, token: str, user_id: str) -> None:
        """
        Blacklist the provided token in Redis with TTL matching its expiry.

        Args:
            token: raw JWT string (access or refresh).
            user_id: ID of the user logging out (for audit logging).
        """
        try:
            payload = self._decode_token(token)
            jti: str = payload.get("jti", "")
            exp: int = payload.get("exp", 0)
            now_ts = int(datetime.now(timezone.utc).timestamp())
            ttl = max(exp - now_ts, 1)
            self._blacklist_token(jti, ttl)
            logger.info("Logged out user %s; blacklisted jti=%s (ttl=%ds)", user_id, jti, ttl)
        except Exception:
            logger.exception("logout_user: error blacklisting token for user %s", user_id)
            raise

    # ──────────────────────────────────────────────────────────────────────

    def verify_email(self, token: str) -> bool:
        """
        Decode email verification token, mark user as verified.

        Returns:
            True on success.

        Raises:
            AuthenticationError: token invalid or expired.
            NotFoundError: user not found.
        """
        try:
            secret = current_app.config["SECRET_KEY"]
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"require": ["sub", "exp", "type"]},
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Verification token has expired.")
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError(f"Invalid verification token: {exc}")

        if payload.get("type") != "email_verify":
            raise AuthenticationError("Invalid token type.")

        user_id: str = payload["sub"]
        user: Optional[User] = User.query.get(user_id)
        if not user:
            raise NotFoundError("User not found.")

        if user.is_email_verified:
            logger.info("Email already verified for user %s", user_id)
            return True

        try:
            user.is_email_verified = True
            db.session.commit()
            logger.info("Email verified for user %s", user_id)
            return True
        except Exception:
            db.session.rollback()
            logger.exception("Failed to mark email verified for user %s", user_id)
            raise

    # ──────────────────────────────────────────────────────────────────────

    def generate_tokens(self, user_id: str, role: str) -> dict:
        """
        Generate JWT access (1hr) and refresh (7day) token pair.

        Returns:
            {access_token: str, refresh_token: str}
        """
        access_token = self._create_access_token(user_id, role)
        refresh_token = self._create_refresh_token(user_id, role)
        return {"access_token": access_token, "refresh_token": refresh_token}

    # ──────────────────────────────────────────────────────────────────────

    def get_user_from_token(self, token: str) -> User:
        """
        Decode JWT, check blacklist, return User.

        Raises:
            AuthenticationError: token invalid, expired, or blacklisted.
            NotFoundError: user not found.
        """
        payload = self._decode_token(token)

        jti: str = payload.get("jti", "")
        if self._is_blacklisted(jti):
            raise AuthenticationError("Token has been revoked.")

        if payload.get("type") != "access":
            raise AuthenticationError("Invalid token type — expected access token.")

        user_id: str = payload["sub"]
        user: Optional[User] = User.query.get(user_id)
        if not user:
            raise NotFoundError("User not found.")
        if not user.is_active:
            raise AuthenticationError("Account is deactivated.", status_code=403)

        return user

    # ──────────────────────────────────────────────────────────────────────

    def generate_password_reset_token(self, user: User) -> str:
        """Generate a short-lived (1hr) password reset token."""
        secret = current_app.config["SECRET_KEY"]
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user.id,
            "jti": str(uuid.uuid4()),
            "type": "password_reset",
            "iat": now,
            "exp": now + timedelta(seconds=PASSWORD_RESET_TOKEN_EXPIRY_SECONDS),
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    def reset_password(self, token: str, new_password: str) -> bool:
        """
        Validate password reset token and update password.

        Raises:
            ValidationError: weak password.
            AuthenticationError: token invalid/expired.
            NotFoundError: user not found.
        """
        if not new_password or len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

        try:
            secret = current_app.config["SECRET_KEY"]
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"require": ["sub", "exp", "type", "jti"]},
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Password reset token has expired.")
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError(f"Invalid reset token: {exc}")

        if payload.get("type") != "password_reset":
            raise AuthenticationError("Invalid token type.")

        jti: str = payload.get("jti", "")
        if self._is_blacklisted(jti):
            raise AuthenticationError("This reset link has already been used.")

        user_id: str = payload["sub"]
        user: Optional[User] = User.query.get(user_id)
        if not user:
            raise NotFoundError("User not found.")

        try:
            user.password_hash = self._hash_password(new_password)
            db.session.commit()
            # Blacklist the reset token so it can't be reused
            exp: int = payload.get("exp", 0)
            now_ts = int(datetime.now(timezone.utc).timestamp())
            ttl = max(exp - now_ts, 1)
            self._blacklist_token(jti, ttl)
            logger.info("Password reset completed for user %s", user_id)
            return True
        except Exception:
            db.session.rollback()
            logger.exception("Failed to reset password for user %s", user_id)
            raise

    # ──────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────

    def _create_access_token(self, user_id: str, role: str) -> str:
        secret = current_app.config["SECRET_KEY"]
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "role": role,
            "jti": str(uuid.uuid4()),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(seconds=ACCESS_TOKEN_EXPIRY_SECONDS),
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    def _create_refresh_token(self, user_id: str, role: str) -> str:
        secret = current_app.config["SECRET_KEY"]
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "role": role,
            "jti": str(uuid.uuid4()),
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(seconds=REFRESH_TOKEN_EXPIRY_SECONDS),
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    def _generate_email_verify_token(self, user_id: str) -> str:
        secret = current_app.config["SECRET_KEY"]
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "jti": str(uuid.uuid4()),
            "type": "email_verify",
            "iat": now,
            "exp": now + timedelta(seconds=EMAIL_VERIFY_TOKEN_EXPIRY_SECONDS),
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    def _decode_token(self, token: str) -> dict:
        """Decode and validate a JWT token. Raises AuthenticationError on failure."""
        try:
            secret = current_app.config["SECRET_KEY"]
            return jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired.")
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError(f"Invalid token: {exc}")

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), password_hash.encode("utf-8")
            )
        except Exception:
            return False

    @staticmethod
    def _is_blacklisted(jti: str) -> bool:
        try:
            return redis_client.exists(f"{BLACKLIST_KEY_PREFIX}{jti}") == 1
        except Exception:
            logger.warning("Redis unavailable — treating token as not blacklisted.")
            return False

    @staticmethod
    def _blacklist_token(jti: str, ttl: int) -> None:
        try:
            redis_client.setex(f"{BLACKLIST_KEY_PREFIX}{jti}", ttl, "1")
        except Exception:
            logger.exception("Failed to blacklist token jti=%s", jti)
            raise

    @staticmethod
    def _serialize_user(user: User) -> dict:
        return {
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
