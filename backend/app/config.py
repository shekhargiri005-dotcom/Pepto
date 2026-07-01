"""
config.py — Configuration hierarchy for the Pepto backend.

Classes:
    BaseConfig: shared settings loaded from environment via pydantic-settings.
    DevelopmentConfig: debug-on, verbose DB echo.
    ProductionConfig: security hardened, no debug.
    TestingConfig: in-memory SQLite, no rate limiting.
"""

from __future__ import annotations

import os
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """Base configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Flask core ────────────────────────────────────────────────────────────
    FLASK_ENV: str = "development"
    SECRET_KEY: str = "changeme-insecure-default"
    DEBUG: bool = False
    TESTING: bool = False

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://pepto_user:pepto_pass@localhost:5432/pepto_db"
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = False

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "changeme-jwt-insecure-default"
    JWT_ACCESS_TOKEN_EXPIRES: int = 3600          # seconds
    JWT_REFRESH_TOKEN_EXPIRES: int = 604800       # 7 days

    # ── Razorpay ──────────────────────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    PLATFORM_FEE_PERCENT: float = 10.0

    # ── Twilio (SMS + 2FA OTP) ────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_VERIFY_SERVICE_SID: str = ""  # Twilio Verify service for OTP

    # ── SendGrid ──────────────────────────────────────────────────────────────
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@pepto.app"

    # ── Cloudinary ────────────────────────────────────────────────────────────
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # ── HuggingFace ───────────────────────────────────────────────────────────
    HUGGINGFACE_API_TOKEN: str = ""

    # ── CORS ──────────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_DEFAULT: str = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL: Optional[str] = None  # falls back to REDIS_URL

    # ── File uploads ──────────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024   # 16 MB

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> List[str]:
        """Allow comma-separated string or list from env."""
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value  # type: ignore[return-value]

    # Convenience aliases expected by Flask-SQLAlchemy and Flask
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:  # noqa: N802
        return self.DATABASE_URL

    def to_flask_dict(self) -> dict:
        """Return a plain dict suitable for app.config.from_mapping()."""
        return {
            "SECRET_KEY": self.SECRET_KEY,
            "DEBUG": self.DEBUG,
            "TESTING": self.TESTING,
            "SQLALCHEMY_DATABASE_URI": self.SQLALCHEMY_DATABASE_URI,
            "SQLALCHEMY_TRACK_MODIFICATIONS": self.SQLALCHEMY_TRACK_MODIFICATIONS,
            "SQLALCHEMY_ECHO": self.SQLALCHEMY_ECHO,
            "JWT_SECRET_KEY": self.JWT_SECRET_KEY,
            "JWT_ACCESS_TOKEN_EXPIRES": self.JWT_ACCESS_TOKEN_EXPIRES,
            "JWT_REFRESH_TOKEN_EXPIRES": self.JWT_REFRESH_TOKEN_EXPIRES,
            "MAX_CONTENT_LENGTH": self.MAX_CONTENT_LENGTH,
            "RATELIMIT_DEFAULT": self.RATE_LIMIT_DEFAULT,
            "RATELIMIT_STORAGE_URL": self.RATELIMIT_STORAGE_URL or self.REDIS_URL,
        }


class DevelopmentConfig(BaseConfig):
    """Development-specific overrides: debug on, verbose SQL."""

    FLASK_ENV: str = "development"
    DEBUG: bool = True
    SQLALCHEMY_ECHO: bool = True
    LOG_LEVEL: str = "DEBUG"


class ProductionConfig(BaseConfig):
    """Production-specific overrides: strict security, no debug."""

    FLASK_ENV: str = "production"
    DEBUG: bool = False
    SQLALCHEMY_ECHO: bool = False
    LOG_LEVEL: str = "WARNING"


class TestingConfig(BaseConfig):
    """Testing overrides: SQLite in-memory, no rate limits, fast JWTs."""

    FLASK_ENV: str = "testing"
    TESTING: bool = True
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///:memory:"
    REDIS_URL: str = "redis://localhost:6379/15"
    JWT_ACCESS_TOKEN_EXPIRES: int = 60
    RATE_LIMIT_DEFAULT: str = "99999 per day"
    SQLALCHEMY_ECHO: bool = False
    LOG_LEVEL: str = "DEBUG"


# ── Config registry ───────────────────────────────────────────────────────────

CONFIG_MAP: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(config_name: str = "development") -> BaseConfig:
    """Instantiate and return the appropriate config object.

    Args:
        config_name: One of 'development', 'production', 'testing'.

    Returns:
        A BaseConfig (or subclass) instance.

    Raises:
        ValueError: If config_name is not recognised.
    """
    config_class = CONFIG_MAP.get(config_name)
    if config_class is None:
        raise ValueError(
            f"Unknown config name '{config_name}'. "
            f"Choose from: {list(CONFIG_MAP.keys())}"
        )
    return config_class()
