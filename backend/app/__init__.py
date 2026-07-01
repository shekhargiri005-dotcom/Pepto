"""
app/__init__.py — Flask application factory for the Pepto backend.

Usage:
    from app import create_app
    app = create_app('development')

The factory:
  1. Loads configuration from the appropriate config class.
  2. Initialises all Flask extensions.
  3. Registers all blueprints under the /api prefix.
  4. Registers error handlers for common HTTP and application errors.
  5. Adds a health-check endpoint at GET /api/health.
  6. Configures structured JSON logging.
"""

from __future__ import annotations

import logging
import logging.config
import os
from datetime import timedelta
from typing import Optional

from flask import Flask, jsonify, request
from flask_jwt_extended.exceptions import (
    InvalidHeaderError,
    JWTDecodeError,
    NoAuthorizationError,
)

from app.config import get_config
from app.extensions import (
    bcrypt,
    cors,
    db,
    init_celery,
    jwt,
    limiter,
    migrate,
    socketio,
)
from app.utils.exceptions import PeptoException


# ── Logging ────────────────────────────────────────────────────────────────────


def _configure_logging(log_level: str = "INFO") -> None:
    """Set up structured JSON-compatible logging.

    Args:
        log_level: One of DEBUG / INFO / WARNING / ERROR / CRITICAL.
    """
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "format": (
                        '{"time": "%(asctime)s", "level": "%(levelname)s", '
                        '"name": "%(name)s", "message": "%(message)s"}'
                    ),
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                },
                "console": {
                    "format": "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
                    "datefmt": "%H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "console",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": log_level,
                "handlers": ["console"],
            },
            "loggers": {
                "gunicorn.error": {"level": "INFO", "propagate": True},
                "gunicorn.access": {"level": "INFO", "propagate": True},
                "sqlalchemy.engine": {
                    "level": "WARNING",
                    "propagate": True,
                },
            },
        }
    )


# ── Application factory ────────────────────────────────────────────────────────


def create_app(config_name: str = "development") -> Flask:
    """Create and configure a Flask application instance.

    Args:
        config_name: Configuration profile — one of
            ``'development'``, ``'production'``, ``'testing'``.

    Returns:
        A fully configured Flask application.
    """
    app = Flask(__name__, instance_relative_config=False)

    # ── 1. Load configuration ─────────────────────────────────────────────────
    config_obj = get_config(config_name)
    app.config.from_mapping(config_obj.to_flask_dict())

    # Store the typed config object so extensions/views can access it
    app.config["APP_CONFIG"] = config_obj

    # JWT timedelta objects (Flask-JWT-Extended accepts int seconds too but
    # explicit timedelta is clearer)
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        seconds=config_obj.JWT_ACCESS_TOKEN_EXPIRES
    )
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(
        seconds=config_obj.JWT_REFRESH_TOKEN_EXPIRES
    )

    # Pass through extra keys needed by extensions
    app.config["CELERY_BROKER_URL"] = config_obj.CELERY_BROKER_URL
    app.config["CELERY_RESULT_BACKEND"] = config_obj.CELERY_RESULT_BACKEND
    app.config["REDIS_URL"] = config_obj.REDIS_URL
    app.config["STRIPE_SECRET_KEY"] = config_obj.STRIPE_SECRET_KEY
    app.config["STRIPE_WEBHOOK_SECRET"] = config_obj.STRIPE_WEBHOOK_SECRET
    app.config["STRIPE_PLATFORM_FEE_PERCENT"] = config_obj.STRIPE_PLATFORM_FEE_PERCENT
    app.config["SENDGRID_API_KEY"] = config_obj.SENDGRID_API_KEY
    app.config["SENDGRID_FROM_EMAIL"] = config_obj.SENDGRID_FROM_EMAIL
    app.config["CLOUDINARY_CLOUD_NAME"] = config_obj.CLOUDINARY_CLOUD_NAME
    app.config["CLOUDINARY_API_KEY"] = config_obj.CLOUDINARY_API_KEY
    app.config["CLOUDINARY_API_SECRET"] = config_obj.CLOUDINARY_API_SECRET
    app.config["FRONTEND_URL"] = config_obj.FRONTEND_URL
    app.config["CORS_ORIGINS"] = config_obj.CORS_ORIGINS

    # ── 2. Configure logging ──────────────────────────────────────────────────
    _configure_logging(config_obj.LOG_LEVEL)
    logger = logging.getLogger(__name__)
    logger.info("Starting Pepto API [env=%s]", config_name)

    # ── 3. Initialise extensions ──────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)

    # CORS — allow configured origins + explicit preflight support
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": config_obj.CORS_ORIGINS}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    # Rate limiter — backed by Redis in production, memory in testing
    limiter.init_app(app)

    # WebSocket
    socketio.init_app(app, message_queue=config_obj.REDIS_URL)

    # Celery
    init_celery(app.config)

    # ── 4. Import / register models (for Alembic) ─────────────────────────────
    with app.app_context():
        import app.models as _models  # noqa: F401  — side-effect import registers all models

    # ── 5. Register blueprints ────────────────────────────────────────────────
    _register_blueprints(app)

    # ── 6. Register error handlers ────────────────────────────────────────────
    _register_error_handlers(app)

    # ── 7. Health check ───────────────────────────────────────────────────────
    @app.get("/api/health")
    def health_check():
        """Lightweight liveness probe used by load balancers and Docker.

        Returns:
            200 JSON with status, environment, and DB connectivity indicator.
        """
        db_ok = False
        try:
            db.session.execute(db.text("SELECT 1"))
            db_ok = True
        except Exception:
            pass

        return (
            jsonify(
                {
                    "status": "ok" if db_ok else "degraded",
                    "environment": config_name,
                    "database": "connected" if db_ok else "unreachable",
                    "version": os.getenv("APP_VERSION", "1.0.0"),
                }
            ),
            200,
        )

    return app


# ── Blueprint registration ─────────────────────────────────────────────────────


def _register_blueprints(app: Flask) -> None:
    """Import and register all API blueprints under the ``/api`` prefix."""

    blueprints = [
        ("app.api.auth",      "auth_bp",      "/api/auth"),
        ("app.api.pets",      "pets_bp",      "/api/pets"),
        ("app.api.reviews",   "reviews_bp",   "/api/reviews"),
        ("app.api.stores",    "stores_bp",    "/api/stores"),
        ("app.api.products",  "products_bp",  "/api/products"),
        ("app.api.orders",    "orders_bp",    "/api/orders"),
        ("app.api.cart",      "cart_bp",      "/api/cart"),
        ("app.api.delivery",  "delivery_bp",  "/api/delivery"),
        ("app.api.nutrition", "nutrition_bp", "/api/nutrition"),
        ("app.api.payments",  "payments_bp",  "/api/payments"),
        ("app.api.admin",     "admin_bp",     "/api/admin"),
        ("app.api.chatbot",   "chatbot_bp",   "/api/chatbot"),
    ]

    for module_path, bp_name, url_prefix in blueprints:
        try:
            import importlib
            module = importlib.import_module(module_path)
            blueprint = getattr(module, bp_name)
            app.register_blueprint(blueprint, url_prefix=url_prefix)
            app.logger.info("Registered blueprint: %s at %s", bp_name, url_prefix)
        except (ImportError, AttributeError) as exc:
            app.logger.warning(
                "Blueprint '%s' not found — skipping (%s)", bp_name, exc
            )

    # WebSocket event handlers
    try:
        import app.sockets  # noqa: F401 — registers @socketio.on handlers
    except ImportError:
        app.logger.warning("sockets module not found — WebSocket events not registered")

    # ── Error handlers ─────────────────────────────────────────────────────────────


def _register_error_handlers(app: Flask) -> None:
    """Attach global JSON error handlers to the application.

    Handlers cover:
    - Custom ``PeptoException`` subclasses
    - Standard HTTP 404 / 405 / 422 / 500 errors
    - Flask-JWT-Extended specific errors

    Args:
        app: The Flask application instance.
    """
    logger = logging.getLogger(__name__)

    # ── Application-level exceptions ──────────────────────────────────────────

    @app.errorhandler(PeptoException)
    def handle_pepto_exception(exc: PeptoException):
        logger.info(
            "PeptoException [%s]: %s", exc.error_code, exc.message
        )
        return jsonify(exc.to_dict()), exc.status_code

    # ── HTTP 404 ──────────────────────────────────────────────────────────────

    @app.errorhandler(404)
    def handle_not_found(exc):
        return (
            jsonify(
                {
                    "error": "NOT_FOUND",
                    "message": f"The endpoint {request.path} does not exist.",
                    "status_code": 404,
                }
            ),
            404,
        )

    # ── HTTP 405 ──────────────────────────────────────────────────────────────

    @app.errorhandler(405)
    def handle_method_not_allowed(exc):
        return (
            jsonify(
                {
                    "error": "METHOD_NOT_ALLOWED",
                    "message": (
                        f"Method {request.method} is not allowed on {request.path}."
                    ),
                    "status_code": 405,
                }
            ),
            405,
        )

    # ── HTTP 422 ──────────────────────────────────────────────────────────────

    @app.errorhandler(422)
    def handle_unprocessable(exc):
        return (
            jsonify(
                {
                    "error": "VALIDATION_ERROR",
                    "message": "The request could not be processed.",
                    "status_code": 422,
                }
            ),
            422,
        )

    # ── HTTP 429 (Flask-Limiter) ───────────────────────────────────────────────

    @app.errorhandler(429)
    def handle_rate_limit(exc):
        return (
            jsonify(
                {
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please slow down.",
                    "status_code": 429,
                }
            ),
            429,
        )

    # ── HTTP 500 ──────────────────────────────────────────────────────────────

    @app.errorhandler(500)
    def handle_server_error(exc):
        logger.exception("Unhandled 500 error: %s", exc)
        return (
            jsonify(
                {
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "status_code": 500,
                }
            ),
            500,
        )

    # ── JWT errors ────────────────────────────────────────────────────────────

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return (
            jsonify(
                {
                    "error": "TOKEN_EXPIRED",
                    "message": "Your session has expired. Please log in again.",
                    "status_code": 401,
                }
            ),
            401,
        )

    @jwt.invalid_token_loader
    def invalid_token_callback(error_string: str):
        return (
            jsonify(
                {
                    "error": "TOKEN_INVALID",
                    "message": f"Invalid token: {error_string}",
                    "status_code": 422,
                }
            ),
            422,
        )

    @jwt.unauthorized_loader
    def missing_token_callback(error_string: str):
        return (
            jsonify(
                {
                    "error": "AUTHORIZATION_REQUIRED",
                    "message": "Request does not contain an access token.",
                    "status_code": 401,
                }
            ),
            401,
        )

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return (
            jsonify(
                {
                    "error": "TOKEN_REVOKED",
                    "message": "The token has been revoked.",
                    "status_code": 401,
                }
            ),
            401,
        )

    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return (
            jsonify(
                {
                    "error": "FRESH_TOKEN_REQUIRED",
                    "message": "A fresh login is required for this action.",
                    "status_code": 401,
                }
            ),
            401,
        )
