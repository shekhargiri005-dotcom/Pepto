"""
utils/exceptions.py — Custom exception hierarchy for the Pepto API.

All exceptions carry:
  - message  : human-readable error description
  - status_code : HTTP status code to return
  - error_code  : machine-readable string constant for API clients

Usage:
    raise NotFoundError("Provider not found", error_code="PROVIDER_NOT_FOUND")
"""

from __future__ import annotations

from typing import Optional


class PeptoException(Exception):
    """Base exception for all application-level errors.

    Args:
        message: Human-readable description of the error.
        status_code: HTTP status code associated with this error.
        error_code: Optional machine-readable error identifier for API clients.
    """

    status_code: int = 500
    default_error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.error_code: str = error_code or self.default_error_code

    def to_dict(self) -> dict:
        """Serialise the exception for JSON API error responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "status_code": self.status_code,
        }


class AuthenticationError(PeptoException):
    """Raised when credentials are missing or invalid (HTTP 401)."""

    status_code = 401
    default_error_code = "AUTHENTICATION_FAILED"

    def __init__(
        self,
        message: str = "Authentication credentials are missing or invalid.",
        error_code: Optional[str] = None,
    ) -> None:
        super().__init__(message, status_code=401, error_code=error_code)


class AuthorizationError(PeptoException):
    """Raised when a user lacks permission to perform an action (HTTP 403)."""

    status_code = 403
    default_error_code = "PERMISSION_DENIED"

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        error_code: Optional[str] = None,
    ) -> None:
        super().__init__(message, status_code=403, error_code=error_code)


class NotFoundError(PeptoException):
    """Raised when a requested resource cannot be found (HTTP 404)."""

    status_code = 404
    default_error_code = "NOT_FOUND"

    def __init__(
        self,
        message: str = "The requested resource was not found.",
        error_code: Optional[str] = None,
    ) -> None:
        super().__init__(message, status_code=404, error_code=error_code)


class ValidationError(PeptoException):
    """Raised when input data fails validation (HTTP 422)."""

    status_code = 422
    default_error_code = "VALIDATION_ERROR"

    def __init__(
        self,
        message: str = "The provided data is invalid.",
        error_code: Optional[str] = None,
        details: Optional[list] = None,
    ) -> None:
        super().__init__(message, status_code=422, error_code=error_code)
        self.details = details or []

    def to_dict(self) -> dict:
        base = super().to_dict()
        base["details"] = self.details
        return base


class ConflictError(PeptoException):
    """Raised on duplicate resource or conflicting state (HTTP 409)."""

    status_code = 409
    default_error_code = "CONFLICT"

    def __init__(
        self,
        message: str = "A resource conflict occurred.",
        error_code: Optional[str] = None,
    ) -> None:
        super().__init__(message, status_code=409, error_code=error_code)


class PaymentError(PeptoException):
    """Raised for payment processing failures (HTTP 402)."""

    status_code = 402
    default_error_code = "PAYMENT_REQUIRED"

    def __init__(
        self,
        message: str = "Payment processing failed.",
        error_code: Optional[str] = None,
    ) -> None:
        super().__init__(message, status_code=402, error_code=error_code)


class RateLimitError(PeptoException):
    """Raised when a client exceeds the allowed request rate (HTTP 429)."""

    status_code = 429
    default_error_code = "RATE_LIMIT_EXCEEDED"

    def __init__(
        self,
        message: str = "Too many requests. Please slow down.",
        error_code: Optional[str] = None,
    ) -> None:
        super().__init__(message, status_code=429, error_code=error_code)


class ServiceUnavailableError(PeptoException):
    """Raised when a downstream service is unavailable (HTTP 503)."""

    status_code = 503
    default_error_code = "SERVICE_UNAVAILABLE"

    def __init__(
        self,
        message: str = "The service is temporarily unavailable. Please try again later.",
        error_code: Optional[str] = None,
    ) -> None:
        super().__init__(message, status_code=503, error_code=error_code)
