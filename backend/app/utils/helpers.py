"""
utils/helpers.py — Utility functions used across the Pepto backend.

Covers: UUID generation, pagination, standard API responses,
Cloudinary uploads, SendGrid emails, geospatial helpers, and Redis caching.
"""

from __future__ import annotations

import json
import logging
import math
import uuid
from typing import Any, Dict, List, Optional, Tuple, Type

import cloudinary
import cloudinary.uploader
from flask import Response, current_app, jsonify
from geopy.distance import geodesic
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)


# ── Identity ──────────────────────────────────────────────────────────────────


def generate_uuid() -> str:
    """Generate a new random UUID4 and return it as a string.

    Returns:
        A hyphenated UUID4 string, e.g. ``'a3bb189e-8bf9-3888-9912-ace4e6543002'``.
    """
    return str(uuid.uuid4())


# ── Pagination ────────────────────────────────────────────────────────────────


def paginate_query(
    query: Any,
    page: int = 1,
    per_page: int = 20,
) -> Dict[str, Any]:
    """Paginate a SQLAlchemy query and return a structured dict.

    Args:
        query: An un-executed SQLAlchemy ``Select`` or ``Query`` object.
        page: 1-based page number.
        per_page: Number of items per page (max enforced: 100).

    Returns:
        A dict with keys: ``items``, ``total``, ``pages``,
        ``current_page``, ``per_page``, ``has_next``, ``has_prev``.
    """
    per_page = min(per_page, 100)
    page = max(page, 1)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        "items": pagination.items,
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page,
        "per_page": per_page,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    }


# ── Standard API responses ────────────────────────────────────────────────────


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
) -> Tuple[Response, int]:
    """Build a standardised success JSON response.

    Args:
        data: Payload to embed under the ``data`` key.
        message: Human-readable success message.
        status_code: HTTP status code (default 200).

    Returns:
        A ``(flask.Response, int)`` tuple ready to be returned from a view.
    """
    payload: Dict[str, Any] = {
        "success": True,
        "message": message,
    }
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status_code


def error_response(
    message: str = "An error occurred.",
    status_code: int = 400,
    error_code: str = "ERROR",
    details: Optional[Any] = None,
) -> Tuple[Response, int]:
    """Build a standardised error JSON response.

    Args:
        message: Human-readable error description.
        status_code: HTTP status code.
        error_code: Machine-readable error constant.
        details: Optional extra detail (list of field errors, etc.).

    Returns:
        A ``(flask.Response, int)`` tuple ready to be returned from a view.
    """
    payload: Dict[str, Any] = {
        "success": False,
        "error": error_code,
        "message": message,
    }
    if details is not None:
        payload["details"] = details
    return jsonify(payload), status_code


# ── Cloudinary ────────────────────────────────────────────────────────────────


def upload_to_cloudinary(file: Any, folder: str = "pepto") -> str:
    """Upload a file object to Cloudinary and return the secure URL.

    Cloudinary credentials are pulled from the Flask app config at call time.

    Args:
        file: A file-like object or local path string accepted by
              ``cloudinary.uploader.upload``.
        folder: Cloudinary folder path (default ``'pepto'``).

    Returns:
        The HTTPS URL of the uploaded resource.

    Raises:
        RuntimeError: If the upload fails.
    """
    config = current_app.config
    cloudinary.config(
        cloud_name=config.get("CLOUDINARY_CLOUD_NAME"),
        api_key=config.get("CLOUDINARY_API_KEY"),
        api_secret=config.get("CLOUDINARY_API_SECRET"),
        secure=True,
    )
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type="auto",
        )
        return result["secure_url"]
    except Exception as exc:
        logger.error("Cloudinary upload failed: %s", exc)
        raise RuntimeError(f"File upload failed: {exc}") from exc


# ── Email ─────────────────────────────────────────────────────────────────────


def send_email(
    to: str,
    subject: str,
    html_content: str,
) -> bool:
    """Send a transactional email via SendGrid.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        html_content: Full HTML body of the email.

    Returns:
        True if the email was accepted by SendGrid (2xx response).
        False on error (logs the exception).
    """
    config = current_app.config
    api_key: str = config.get("SENDGRID_API_KEY", "")
    from_email: str = config.get("SENDGRID_FROM_EMAIL", "noreply@pepto.app")

    if not api_key:
        logger.warning("SENDGRID_API_KEY not configured; email not sent to %s", to)
        return False

    message = Mail(
        from_email=from_email,
        to_emails=to,
        subject=subject,
        html_content=html_content,
    )
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logger.info(
            "Email sent to %s [status=%s]", to, response.status_code
        )
        return response.status_code in (200, 201, 202)
    except Exception as exc:
        logger.error("SendGrid error sending to %s: %s", to, exc)
        return False


# ── Geospatial ────────────────────────────────────────────────────────────────


def calculate_distance_km(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> float:
    """Calculate the great-circle distance between two points using geopy.

    Args:
        lat1: Latitude of point A (degrees).
        lng1: Longitude of point A (degrees).
        lat2: Latitude of point B (degrees).
        lng2: Longitude of point B (degrees).

    Returns:
        Distance in kilometres, rounded to 3 decimal places.
    """
    distance = geodesic((lat1, lng1), (lat2, lng2))
    return round(distance.kilometers, 3)


def validate_coordinates(lat: float, lng: float) -> bool:
    """Validate that latitude and longitude are within valid ranges.

    Args:
        lat: Latitude, must be in [-90, 90].
        lng: Longitude, must be in [-180, 180].

    Returns:
        True if both coordinates are valid; False otherwise.
    """
    try:
        return -90.0 <= float(lat) <= 90.0 and -180.0 <= float(lng) <= 180.0
    except (TypeError, ValueError):
        return False


# ── Redis caching helpers ─────────────────────────────────────────────────────


def get_redis_client():  # type: ignore[return]
    """Return the shared Redis client configured in extensions.

    Returns:
        A ``redis.Redis`` instance bound to the URL from app config.
    """
    from app.extensions import get_redis

    redis_url: str = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
    return get_redis(redis_url)


def cache_get(key: str) -> Optional[Any]:
    """Retrieve a JSON-serialised value from Redis.

    Args:
        key: Cache key string.

    Returns:
        The deserialised Python object, or ``None`` if the key does not exist.
    """
    try:
        client = get_redis_client()
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning("cache_get error for key '%s': %s", key, exc)
        return None


def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """Store a JSON-serialised value in Redis with an expiry.

    Args:
        key: Cache key string.
        value: Any JSON-serialisable Python object.
        ttl: Time-to-live in seconds (default 300 = 5 min).

    Returns:
        True if the value was stored successfully; False on error.
    """
    try:
        client = get_redis_client()
        client.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as exc:
        logger.warning("cache_set error for key '%s': %s", key, exc)
        return False


def cache_delete(key: str) -> bool:
    """Delete a key from the Redis cache.

    Args:
        key: Cache key to remove.

    Returns:
        True if the key was deleted; False on error.
    """
    try:
        client = get_redis_client()
        client.delete(key)
        return True
    except Exception as exc:
        logger.warning("cache_delete error for key '%s': %s", key, exc)
        return False
