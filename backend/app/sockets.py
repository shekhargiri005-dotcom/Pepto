"""
sockets.py — Flask-SocketIO event handlers for real-time delivery tracking.

Events (Client → Server):
    join_order_room     : Customer or store joins a room to watch an order.
    join_store_room     : Store owner joins their room to receive new orders.
    location_update     : Delivery partner pushes GPS coordinates.
    order_status_change : Store owner updates order status.

Events (Server → Client):
    location_updated    : Broadcast to order room — new partner location.
    order_status_updated: Broadcast to order room — status changed.
    new_order           : Sent to store room when a customer places an order.
    delivery_assigned   : Sent to delivery partner when assigned an order.
    error               : Sent back to caller on validation failure.
"""

from __future__ import annotations

import logging

from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import emit, join_room, leave_room

from app.extensions import socketio

logger = logging.getLogger(__name__)


# ── Room management ───────────────────────────────────────────────────────────


@socketio.on("join_order_room")
def on_join_order_room(data: dict) -> None:
    """Customer or store owner subscribes to live updates for an order.

    Args:
        data: {"order_id": "<uuid>"}
    """
    order_id = data.get("order_id")
    if not order_id:
        emit("error", {"message": "order_id is required"})
        return
    room = f"order_{order_id}"
    join_room(room)
    logger.debug("Client %s joined room %s", request.sid, room)
    emit("joined", {"room": room})


@socketio.on("join_store_room")
def on_join_store_room(data: dict) -> None:
    """Store owner subscribes to new-order notifications for their store.

    Args:
        data: {"store_id": "<uuid>"}
    """
    store_id = data.get("store_id")
    if not store_id:
        emit("error", {"message": "store_id is required"})
        return
    room = f"store_{store_id}"
    join_room(room)
    logger.debug("Store owner %s joined room %s", request.sid, room)
    emit("joined", {"room": room})


@socketio.on("join_partner_room")
def on_join_partner_room(data: dict) -> None:
    """Delivery partner joins their personal notification room.

    Args:
        data: {"partner_id": "<uuid>"}
    """
    partner_id = data.get("partner_id")
    if not partner_id:
        emit("error", {"message": "partner_id is required"})
        return
    room = f"partner_{partner_id}"
    join_room(room)
    emit("joined", {"room": room})


# ── Real-time location updates ────────────────────────────────────────────────


@socketio.on("location_update")
def on_location_update(data: dict) -> None:
    """Delivery partner broadcasts their current GPS position.

    The event is persisted to DeliveryTracking and broadcast to the
    order room so the customer's map updates in real-time.

    Args:
        data: {
            "order_id": "<uuid>",
            "partner_id": "<uuid>",
            "lat": 12.9716,
            "lng": 77.5946
        }
    """
    order_id = data.get("order_id")
    lat = data.get("lat")
    lng = data.get("lng")
    partner_id = data.get("partner_id")

    if not all([order_id, lat, lng, partner_id]):
        emit("error", {"message": "order_id, partner_id, lat, lng are required"})
        return

    # Persist tracking log
    try:
        from app.extensions import db
        from app.models.delivery_tracking import DeliveryTracking
        from app.models.delivery_partner import DeliveryPartner

        # Update partner's live position
        partner = DeliveryPartner.query.get(partner_id)
        if partner:
            partner.current_lat = lat
            partner.current_lng = lng
            db.session.add(DeliveryTracking(
                order_id=order_id,
                delivery_partner_id=partner_id,
                lat=lat,
                lng=lng,
                status="in_transit",
            ))
            db.session.commit()
    except Exception as exc:
        logger.warning("Failed to persist location update: %s", exc)

    # Broadcast to order room
    room = f"order_{order_id}"
    emit(
        "location_updated",
        {"lat": lat, "lng": lng, "partner_id": partner_id, "order_id": order_id},
        room=room,
        include_self=False,
    )
    logger.debug("Location update for order %s: (%.4f, %.4f)", order_id, lat, lng)


# ── Order status changes ──────────────────────────────────────────────────────


@socketio.on("order_status_change")
def on_order_status_change(data: dict) -> None:
    """Store owner or delivery partner pushes a status change.

    Args:
        data: {"order_id": "<uuid>", "status": "<OrderStatus value>"}
    """
    order_id = data.get("order_id")
    status = data.get("status")

    if not order_id or not status:
        emit("error", {"message": "order_id and status are required"})
        return

    room = f"order_{order_id}"
    emit(
        "order_status_updated",
        {"order_id": order_id, "status": status},
        room=room,
    )
    logger.info("Order %s status → %s (broadcast to room)", order_id, status)


# ── Helper: notify from application code ─────────────────────────────────────


def notify_new_order(store_id: str, order_data: dict) -> None:
    """Push a new-order notification to a store's room.

    Called from the order service after a customer places an order.
    """
    socketio.emit("new_order", order_data, room=f"store_{store_id}")


def notify_delivery_assigned(partner_id: str, order_data: dict) -> None:
    """Push a delivery assignment notification to a partner's room.

    Called from the delivery service after assigning an order.
    """
    socketio.emit("delivery_assigned", order_data, room=f"partner_{partner_id}")


def notify_order_status(order_id: str, status: str, extra: dict | None = None) -> None:
    """Utility to broadcast an order status change from anywhere in the app."""
    payload = {"order_id": order_id, "status": status, **(extra or {})}
    socketio.emit("order_status_updated", payload, room=f"order_{order_id}")
