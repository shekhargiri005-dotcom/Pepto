"""
models/base.py — Abstract mixin that provides UUID PK, timestamps, and soft delete.

All Pepto models should inherit from both ``db.Model`` and ``BaseMixin``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


def _utcnow() -> datetime:
    """Return a tz-aware UTC datetime."""
    return datetime.now(timezone.utc)


class BaseMixin:
    """Mixin providing UUID primary key, audit timestamps, and soft delete.

    Usage:
        class MyModel(BaseMixin, db.Model):
            __tablename__ = 'my_models'
            ...
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # ── Soft delete helpers ───────────────────────────────────────────────────

    @property
    def is_deleted(self) -> bool:
        """True when the record has been soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark this record as deleted without removing it from the database.

        Callers must still call ``db.session.commit()`` to persist the change.
        """
        self.deleted_at = _utcnow()

    def restore(self) -> None:
        """Undo a soft delete, making the record active again."""
        self.deleted_at = None

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(
        self,
        exclude: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Serialise the model to a plain dictionary.

        Args:
            exclude: Optional list of column names to omit from the output.
                     Use this to strip sensitive fields such as ``password_hash``.

        Returns:
            A dict mapping column names to Python-native values.
            UUID and datetime values are converted to strings.
        """
        _exclude: List[str] = exclude or []
        result: Dict[str, Any] = {}

        for column in self.__table__.columns:  # type: ignore[attr-defined]
            if column.name in _exclude:
                continue
            value = getattr(self, column.name)
            if isinstance(value, uuid.UUID):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value

        return result

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.__class__.__name__} id={self.id}>"
