from .auth import auth_bp
from .providers import providers_bp
from .bookings import bookings_bp
from .payments import payments_bp
from .reviews import reviews_bp
from .pets import pets_bp
from .chatbot import chatbot_bp
from .admin import admin_bp

__all__ = [
    'auth_bp',
    'providers_bp',
    'bookings_bp',
    'payments_bp',
    'reviews_bp',
    'pets_bp',
    'chatbot_bp',
    'admin_bp'
]
