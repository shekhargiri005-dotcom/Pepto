"""
utils/decorators.py — Reusable view decorators for the Pepto API.

Includes:
    require_auth       — enforce valid JWT and load current_user onto flask.g
    require_role       — RBAC role enforcement
    validate_json      — Pydantic request body validation
    cache_response     — Redis response caching
    provider_required  — shortcut for require_role('provider')
    admin_required     — shortcut for require_role('admin')
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
from typing import Any, Callable, Optional, Tuple, Type

from flask import Response, g, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from pydantic import BaseModel, ValidationError as PydanticValidationError

from app.utils.exceptions import AuthenticationError, AuthorizationError, ValidationError

logger = logging.getLogger(__name__)

# Type alias for view functions
ViewFunc = Callable[..., Any]


# ── JWT / Authentication ──────────────────────────────────────────────────────


def require_auth(fn: ViewFunc) -> ViewFunc:
    """Decorator: verify the JWT in the Authorization header and load the user.

    Sets ``flask.g.current_user`` to the loaded ``User`` model instance.

    Raises:
        AuthenticationError: If the token is missing, expired, or invalid.
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            verify_jwt_in_request()
        except Exception as exc:
            raise AuthenticationError(
                "Invalid or missing authentication token.",
                error_code="TOKEN_INVALID",
            ) from exc

        user_id: str = get_jwt_identity()
        from app.models.user import User

        user = User.query.filter_by(id=user_id, is_active=True).first()
        if user is None:
            raise AuthenticationError(
                "User account not found or deactivated.",
                error_code="USER_NOT_FOUND",
            )
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


# ── Role-based access control ─────────────────────────────────────────────────


def require_role(*roles: str) -> Callable[[ViewFunc], ViewFunc]:
    """Decorator factory: restrict a view to users with one of the given roles.

    Must be applied **after** ``@require_auth`` so that ``g.current_user`` is set.

    Args:
        roles: One or more allowed role strings (e.g. ``'admin'``, ``'provider'``).

    Returns:
        A decorator that wraps the view function.

    Raises:
        AuthorizationError: If the current user's role is not in *roles*.

    Example:
        @require_auth
        @require_role('provider', 'admin')
        def my_view(): ...
    """

    def decorator(fn: ViewFunc) -> ViewFunc:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = getattr(g, "current_user", None)
            if user is None:
                raise AuthenticationError(error_code="NO_AUTH_CONTEXT")
            role_value = (
                user.role.value if hasattr(user.role, "value") else str(user.role)
            )
            if role_value not in roles:
                raise AuthorizationError(
                    f"Access restricted to roles: {', '.join(roles)}.",
                    error_code="INSUFFICIENT_ROLE",
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator


# ── Pydantic request validation ───────────────────────────────────────────────


def validate_json(schema_class: Type[BaseModel]) -> Callable[[ViewFunc], ViewFunc]:
    """Decorator factory: validate the incoming JSON body against a Pydantic schema.

    On success, injects the validated model instance as the first keyword
    argument ``validated_data`` to the wrapped view.

    On failure, returns a 422 JSON response with Pydantic field-level errors.

    Args:
        schema_class: A Pydantic ``BaseModel`` subclass to validate against.

    Returns:
        A decorator.

    Example:
        @require_auth
        @validate_json(RegisterRequest)
        def register(validated_data: RegisterRequest): ...
    """

    def decorator(fn: ViewFunc) -> ViewFunc:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not request.is_json:
                raise ValidationError(
                    "Request body must be JSON (Content-Type: application/json).",
                    error_code="INVALID_CONTENT_TYPE",
                )
            raw_body = request.get_json(silent=True) or {}
            try:
                validated = schema_class(**raw_body)
            except PydanticValidationError as exc:
                errors = [
                    {
                        "field": ".".join(str(loc) for loc in err["loc"]),
                        "message": err["msg"],
                        "type": err["type"],
                    }
                    for err in exc.errors()
                ]
                raise ValidationError(
                    "Request validation failed.",
                    error_code="VALIDATION_ERROR",
                    details=errors,
                )
            kwargs["validated_data"] = validated
            return fn(*args, **kwargs)

        return wrapper

    return decorator


# ── Redis response caching ────────────────────────────────────────────────────


def cache_response(
    ttl: int = 300,
    key_prefix: str = "",
) -> Callable[[ViewFunc], ViewFunc]:
    """Decorator factory: cache the full Flask JSON response in Redis.

    The cache key is built from *key_prefix* + SHA256 of the request path
    and query string.  Authenticated requests include the user ID in the key
    so each user gets their own cached response.

    Args:
        ttl: Cache lifetime in seconds (default 300 = 5 min).
        key_prefix: Optional string prepended to the cache key.

    Returns:
        A decorator.
    """

    def decorator(fn: ViewFunc) -> ViewFunc:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from app.utils.helpers import cache_get, cache_set

            # Build a unique cache key
            user_id = getattr(getattr(g, "current_user", None), "id", "anon")
            raw_key = f"{key_prefix}:{user_id}:{request.full_path}"
            cache_key = hashlib.sha256(raw_key.encode()).hexdigest()

            cached = cache_get(cache_key)
            if cached is not None:
                response = jsonify(cached)
                response.headers["X-Cache"] = "HIT"
                return response

            result = fn(*args, **kwargs)

            # Normalise the return value
            if isinstance(result, tuple):
                response_obj, status_code = result[0], result[1]
            else:
                response_obj, status_code = result, 200

            if hasattr(response_obj, "get_json"):
                response_data = response_obj.get_json()
                if response_data is not None and status_code == 200:
                    cache_set(cache_key, response_data, ttl)

            if isinstance(result, tuple):
                return result
            return result

        return wrapper

    return decorator


# ── Convenience role shortcuts ────────────────────────────────────────────────


def provider_required(fn: ViewFunc) -> ViewFunc:
    """Shortcut: ``@require_auth`` + ``@require_role('provider')``."""

    @require_auth
    @require_role("provider")
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn: ViewFunc) -> ViewFunc:
    """Shortcut: ``@require_auth`` + ``@require_role('admin')``."""

    @require_auth
    @require_role("admin")
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return fn(*args, **kwargs)

    return wrapper
