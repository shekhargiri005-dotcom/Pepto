"""
schemas/auth_schemas.py — Pydantic request/response models for authentication.
"""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class RegisterRequest(BaseModel):
    """Schema for ``POST /api/auth/register``.

    Enforces:
    - valid email format
    - password of at least 8 characters with both upper-case and lower-case letters
    - role defaults to 'customer'
    """

    email: EmailStr = Field(..., description="User's email address (login identifier)")
    phone: Optional[str] = Field(
        None,
        min_length=7,
        max_length=20,
        description="Optional phone number (E.164 recommended)",
    )
    full_name: str = Field(
        ..., min_length=2, max_length=200, description="Display name"
    )
    password: str = Field(
        ..., min_length=8, description="Password — min 8 chars, mixed case required"
    )
    role: UserRole = Field(
        UserRole.customer, description="Account role: customer | provider | admin"
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        """Ensure password contains both upper-case and lower-case characters."""
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter.")
        return value

    @field_validator("phone")
    @classmethod
    def phone_format(cls, value: Optional[str]) -> Optional[str]:
        """Strip non-digit characters and validate basic length."""
        if value is None:
            return None
        digits = re.sub(r"\D", "", value)
        if len(digits) < 7 or len(digits) > 15:
            raise ValueError("Phone number must have between 7 and 15 digits.")
        return value


class LoginRequest(BaseModel):
    """Schema for ``POST /api/auth/login``."""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Account password")


class RefreshRequest(BaseModel):
    """Schema for ``POST /api/auth/refresh``."""

    refresh_token: str = Field(..., description="A valid refresh JWT")


class ForgotPasswordRequest(BaseModel):
    """Schema for ``POST /api/auth/forgot-password``."""

    email: EmailStr = Field(
        ..., description="Email address associated with the account"
    )


class ResetPasswordRequest(BaseModel):
    """Schema for ``POST /api/auth/reset-password``."""

    token: str = Field(..., description="Password-reset token from the email link")
    new_password: str = Field(
        ..., min_length=8, description="New password — min 8 chars, mixed case"
    )

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, value: str) -> str:
        """Enforce mixed-case requirement on the new password."""
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter.")
        return value
