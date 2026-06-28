"""
extensions.py — Flask extension singletons (lazy-init pattern).

All extensions are instantiated here WITHOUT a Flask app instance.
They are wired to the app inside the create_app() factory via ``init_app()``.
Import these objects wherever you need them — they carry the bound app context
at runtime without creating circular imports.
"""

from __future__ import annotations

from typing import Optional

import redis as redis_lib
from celery import Celery
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

# ── Core ORM & migrations ────────────────────────────────────────────────────
db: SQLAlchemy = SQLAlchemy()
migrate: Migrate = Migrate()

# ── Auth ──────────────────────────────────────────────────────────────────────
jwt: JWTManager = JWTManager()
bcrypt: Bcrypt = Bcrypt()

# ── Cross-Origin Resource Sharing ─────────────────────────────────────────────
cors: CORS = CORS()

# ── Rate limiting ─────────────────────────────────────────────────────────────
limiter: Limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",          # overridden in create_app via config
)

# ── WebSocket support ─────────────────────────────────────────────────────────
socketio: SocketIO = SocketIO(
    cors_allowed_origins="*",
    async_mode="eventlet",
    logger=False,
    engineio_logger=False,
)

# ── Celery (configured outside create_app; see celery_app.py) ─────────────────
celery: Celery = Celery(__name__)

# ── Redis client (module-level singleton, initialised lazily) ─────────────────
_redis_client: Optional[redis_lib.Redis] = None  # type: ignore[type-arg]


def get_redis(url: str = "redis://localhost:6379/0") -> redis_lib.Redis:  # type: ignore[type-arg]
    """Return a shared Redis client, creating it on first call.

    Args:
        url: Redis connection URL (defaults to REDIS_URL from config).

    Returns:
        A connected ``redis.Redis`` instance.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.from_url(url, decode_responses=True)
    return _redis_client


def init_celery(app_config: dict) -> Celery:
    """Configure the global Celery instance from Flask app config.

    Args:
        app_config: Flat dict from ``flask_app.config``.

    Returns:
        The configured ``Celery`` instance.
    """
    celery.conf.update(
        broker_url=app_config.get("CELERY_BROKER_URL", "redis://localhost:6379/1"),
        result_backend=app_config.get(
            "CELERY_RESULT_BACKEND", "redis://localhost:6379/2"
        ),
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        worker_prefetch_multiplier=1,
    )
    return celery
