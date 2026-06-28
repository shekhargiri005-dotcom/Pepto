# ============================================================
# Pepto Backend — Multi-Stage Docker Build
# Stage 1: builder  |  Stage 2: production
# ============================================================

# ── Stage 1: builder ─────────────────────────────────────────
FROM python:3.11-slim AS builder

LABEL maintainer="Pepto Engineering <engineering@pepto.app>"
LABEL description="Pepto Pet Services Marketplace — Backend Builder"

# Install system-level build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libpq-dev \
        libffi-dev \
        libssl-dev \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy requirements first for layer caching
COPY requirements.txt .

# Create a virtualenv and install all Python dependencies into it
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ── Stage 2: production ──────────────────────────────────────
FROM python:3.11-slim AS production

LABEL maintainer="Pepto Engineering <engineering@pepto.app>"
LABEL description="Pepto Pet Services Marketplace — Backend Production"
LABEL version="1.0.0"

# Install only runtime system dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libffi8 \
        libssl3 \
        curl \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and group
RUN groupadd --gid 1001 pepto && \
    useradd  --uid 1001 --gid pepto --shell /bin/bash --create-home pepto

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Make sure the venv binaries take precedence
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    FLASK_ENV=production \
    PORT=5000

WORKDIR /app

# Copy application source code
COPY --chown=pepto:pepto . .

# Create directories that the app may need at runtime
RUN mkdir -p /app/staticfiles /app/media /app/logs && \
    chown -R pepto:pepto /app

# Drop to non-root user
USER pepto

EXPOSE 5000

# Health-check — the container is healthy when /api/health returns 200
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fs http://localhost:5000/api/health || exit 1

# Gunicorn is configured via gunicorn.conf.py at the project root
CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
