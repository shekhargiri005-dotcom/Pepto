"""
wsgi.py — WSGI entry point for production deployments.

Used by Gunicorn:
    gunicorn wsgi:app -c gunicorn.conf.py

The application object must be named ``app`` so that Gunicorn can find it
via the ``wsgi:app`` target.
"""

from __future__ import annotations

from app import create_app

# Create the production application instance.
app = create_app("production")

if __name__ == "__main__":
    # Fallback for running directly with ``python wsgi.py`` (not recommended
    # in production — use Gunicorn instead).
    app.run(host="0.0.0.0", port=5000)
