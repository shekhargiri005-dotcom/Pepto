"""
models/notification.py — In-app notification stored per user.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseMixin

if TYPE_CHECKING:
    from app.models.user import User


class Notification(BaseMixin, db.Model):
    """An in-app notification for a user.

    type examples:
        order_confirmed, order_preparing, order_out_for_delivery,
        order_delivered, order_cancelled, new_order (for stores),
        delivery_assigned (for partners), review_received

    related_entity_type / related_entity_id:
        Allow the frontend to deep-link into the relevant resource.
        e.g., type="order_confirmed", related_entity_type="order", related_entity_id=<order_id>
    """

    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    related_entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    user: Mapped["User"] = relationship("User")
