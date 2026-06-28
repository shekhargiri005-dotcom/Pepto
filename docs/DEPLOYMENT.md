# =============================================================================
# Pepto — Deployment Guide
# =============================================================================

This guide covers deploying Pepto to three different platforms, from the simplest free-tier option to a self-managed VPS.

> [!IMPORTANT]
> Always deploy with HTTPS. Never expose your `.env` secrets in source control.
> PostGIS (the `postgis/postgis` image) is required — standard PostgreSQL images will not work.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Variables](#environment-variables)
3. [Railway (Recommended — Free Tier)](#1-railway-recommended--free-tier)
4. [Render](#2-render)
5. [AWS EC2 with Docker Compose](#3-aws-ec2-with-docker-compose)
6. [PostGIS Setup Notes](#postgis-setup-notes)
7. [SSL / TLS with Let's Encrypt](#ssl--tls-with-lets-encrypt)
8. [Stripe Webhook Configuration](#stripe-webhook-configuration)
9. [Celery in Production](#celery-in-production)
10. [Monitoring & Observability](#monitoring--observability)

---

## Prerequisites

- Docker 24+ and Docker Compose v2+
- A domain name pointed at your server (A record)
- Accounts: Stripe, Cloudinary, Mapbox
- SMTP credentials (SendGrid recommended)

---

## Environment Variables

Create `backend/.env` from the template:

```bash
cp backend/.env.example backend/.env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | Flask secret key — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_SECRET_KEY` | ✅ | JWT signing key — generate separately from SECRET_KEY |
| `DATABASE_URL` | ✅ | PostgreSQL connection string e.g. `postgresql://user:pass@host/db` |
| `REDIS_URL` | ✅ | Redis connection string e.g. `redis://localhost:6379/0` |
| `STRIPE_SECRET_KEY` | ✅ | Stripe secret key (`sk_live_...`) |
| `STRIPE_PUBLISHABLE_KEY` | ✅ | Stripe publishable key (`pk_live_...`) |
| `STRIPE_WEBHOOK_SECRET` | ✅ | Stripe webhook signing secret (`whsec_...`) |
| `CLOUDINARY_URL` | ✅ | Full Cloudinary URL including API key and secret |
| `MAPBOX_SECRET_TOKEN` | ✅ | Mapbox secret token for server-side geocoding |
| `MAIL_SERVER` | ✅ | SMTP server hostname |
| `MAIL_PORT` | ✅ | SMTP port (587 for TLS) |
| `MAIL_USERNAME` | ✅ | SMTP username |
| `MAIL_PASSWORD` | ✅ | SMTP password |
| `MAIL_DEFAULT_SENDER` | ✅ | From address e.g. `noreply@pepto.app` |
| `SENTRY_DSN` | ⚠️ | Sentry DSN for error tracking |
| `FLASK_ENV` | ✅ | `production` |
| `CORS_ORIGINS` | ✅ | Comma-separated allowed origins e.g. `https://pepto.app` |
| `PLATFORM_FEE_PERCENT` | ✅ | Marketplace fee percentage e.g. `10` |

---

## 1. Railway (Recommended — Free Tier)

Railway provides managed Postgres (with PostGIS), Redis, and auto-deploy from GitHub. The free tier is sufficient for early-stage traffic.

### Step 1 — Create a Railway project

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
2. Select your `pepto` repository
3. Railway detects `docker-compose.yml` automatically

### Step 2 — Add services

In your Railway project, click **+ New**:

1. **PostgreSQL** → choose **postgis/postgis:16-3.4** as the custom image  
   *(or use Railway's managed Postgres and enable the PostGIS extension)*
2. **Redis** → select from the plugin catalogue

### Step 3 — Environment variables

In the Railway **Variables** tab for each service, add all the variables from the table above.

```
# Set on the backend service
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

### Step 4 — Set up custom domain

Railway Settings → **Custom Domain** → enter `api.pepto.app` and follow DNS instructions.

### Step 5 — Deploy

Push to `main`. Railway will:
1. Pull your Docker images
2. Run `flask db upgrade` via the **Start Command**
3. Expose your service on the custom domain

**Recommended `railway.toml`:**
```toml
[build]
builder = "dockerfile"
dockerfilePath = "backend/Dockerfile"

[deploy]
startCommand = "flask db upgrade && gunicorn -c gunicorn.conf.py wsgi:app"
healthcheckPath = "/api/health"
healthcheckTimeout = 300
restartPolicyType = "on_failure"
```

---

## 2. Render

Render offers a generous free tier with auto-deploy, managed Postgres, and Redis.

### Step 1 — Create services

1. **Web Service** → connect GitHub → select `pepto` → choose **Docker** environment
   - Build: `./backend/Dockerfile`
   - Start command: `gunicorn -c gunicorn.conf.py wsgi:app`
   - Health check path: `/api/health`

2. **PostgreSQL** (Render Managed) → enable `postgis` extension after creation:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   CREATE EXTENSION IF NOT EXISTS postgis_topology;
   ```

3. **Redis** → create a Render Redis instance

4. **Background Worker** (Celery) → new Background Worker service
   - Same Docker image as backend
   - Start command: `celery -A celery_app worker --loglevel=info --concurrency=4`

### Step 2 — Environment groups

Create a **Render Environment Group** called `pepto-production` and add all secrets. Reference it in each service to avoid duplication.

### Step 3 — Custom domain

Dashboard → Custom Domains → add `pepto.app` and `api.pepto.app`. Render provisions Let's Encrypt SSL automatically.

---

## 3. AWS EC2 with Docker Compose

Best for full control, horizontal scaling, and production traffic.

### Step 1 — Launch an EC2 instance

```
Instance type: t3.medium (2 vCPU, 4 GB RAM) minimum
AMI: Ubuntu 24.04 LTS
Storage: 30 GB gp3 SSD
Security groups:
  - SSH (22): your IP only
  - HTTP (80): 0.0.0.0/0
  - HTTPS (443): 0.0.0.0/0
```

### Step 2 — Install Docker

```bash
# SSH into your instance
ssh -i pepto-key.pem ubuntu@<EC2_PUBLIC_IP>

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
newgrp docker

# Install Docker Compose plugin
sudo apt-get install -y docker-compose-plugin

# Verify
docker compose version
```

### Step 3 — Clone the repository

```bash
git clone https://github.com/your-org/pepto.git /opt/pepto
cd /opt/pepto

# Set up environment
cp backend/.env.example backend/.env
nano backend/.env   # Fill in all production values
```

### Step 4 — Set up SSL (see section below)

### Step 5 — Start the application

```bash
# Pull images and start all services
docker compose pull
docker compose up -d

# Run migrations
docker compose exec backend flask db upgrade

# Verify health
curl http://localhost:5000/api/health
```

### Step 6 — Configure systemd for auto-restart

```bash
sudo tee /etc/systemd/system/pepto.service > /dev/null <<EOF
[Unit]
Description=Pepto Docker Compose Application
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/pepto
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0
User=ubuntu

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable pepto
sudo systemctl start pepto
```

### Step 7 — Enable automatic updates (Watchtower)

```bash
docker run -d \
  --name watchtower \
  --restart always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --schedule "0 0 4 * * *" \
  --cleanup \
  pepto-backend pepto-frontend
```

---

## PostGIS Setup Notes

PostGIS is the geospatial extension for PostgreSQL, required for location-based provider search.

### Verify PostGIS is enabled

```bash
docker compose exec postgres psql -U pepto_user -d pepto_db -c "SELECT PostGIS_version();"
```

### Enable extensions after first run

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;
```

### Creating a spatial index (in Flask-Migrate migration)

```python
from geoalchemy2 import Geometry
from sqlalchemy import Index

# In your model:
location = db.Column(Geometry('POINT', srid=4326))

# In migration:
op.execute("CREATE INDEX idx_providers_location ON providers USING GIST (location);")
```

---

## SSL / TLS with Let's Encrypt

### Using Certbot + nginx

```bash
# Install certbot on the host
sudo apt install certbot

# Stop nginx temporarily
docker compose stop nginx

# Obtain certificate
sudo certbot certonly --standalone \
  -d pepto.app \
  -d www.pepto.app \
  -d api.pepto.app \
  --email engineering@pepto.app \
  --agree-tos \
  --no-eff-email

# Copy certs into the Docker volume
sudo cp /etc/letsencrypt/live/pepto.app/fullchain.pem /var/lib/docker/volumes/pepto_ssl_certs/_data/
sudo cp /etc/letsencrypt/live/pepto.app/privkey.pem   /var/lib/docker/volumes/pepto_ssl_certs/_data/

# Generate DH params (one-time, takes ~5 minutes)
sudo openssl dhparam -out /var/lib/docker/volumes/pepto_ssl_certs/_data/dhparam.pem 4096

# Restart nginx
docker compose start nginx
```

### Auto-renewal cron job

```bash
# Add to root crontab: sudo crontab -e
0 3 * * * certbot renew --quiet --deploy-hook "docker compose -f /opt/pepto/docker-compose.yml restart nginx"
```

---

## Stripe Webhook Configuration

1. In the [Stripe Dashboard](https://dashboard.stripe.com/webhooks) → **Add endpoint**
2. Endpoint URL: `https://pepto.app/api/payments/webhook`
3. Select events:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `charge.refunded`
   - `customer.subscription.created`
   - `customer.subscription.deleted`
4. Copy the **Signing Secret** (`whsec_...`) to your `.env` as `STRIPE_WEBHOOK_SECRET`

### Test webhooks locally

```bash
stripe listen --forward-to localhost:5000/api/payments/webhook
```

---

## Celery in Production

### Recommended configuration (`backend/celery_config.py`)

```python
# Broker & result backend
broker_url = os.environ["REDIS_URL"]
result_backend = os.environ["REDIS_URL"]

# Queues
task_queues = {
    "default":      Queue("default"),
    "emails":       Queue("emails"),
    "notifications": Queue("notifications"),
    "payments":     Queue("payments"),
}
task_default_queue = "default"

# Concurrency & performance
worker_concurrency = 4
worker_prefetch_multiplier = 1   # Fair task distribution
task_acks_late = True            # Only ack after task completes
worker_max_tasks_per_child = 500 # Restart worker to prevent memory leaks

# Serialization
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
enable_utc = True

# Retry defaults
task_default_retry_delay = 60      # 1 minute
task_max_retries = 3
```

### Monitoring Celery with Flower

```yaml
# Add to docker-compose.yml
flower:
  image: mher/flower
  command: celery --broker=redis://redis:6379/0 flower --port=5555
  ports:
    - "5555:5555"
  depends_on:
    - redis
  networks:
    - pepto_network
```

Access Flower dashboard at `http://your-server:5555` (put behind nginx auth in production).

---

## Monitoring & Observability

### Sentry (Error Tracking)

```bash
pip install sentry-sdk[flask]
```

```python
# In app/__init__.py
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    integrations=[FlaskIntegration(), CeleryIntegration(), SqlalchemyIntegration()],
    traces_sample_rate=0.2,
    profiles_sample_rate=0.1,
    environment=os.environ.get("FLASK_ENV", "production"),
)
```

### UptimeRobot

1. Sign up at [uptimerobot.com](https://uptimerobot.com) (free tier: 50 monitors)
2. Add HTTP(s) monitor → URL: `https://pepto.app/api/health`
3. Alert contacts: email + Slack webhook
4. Check interval: every 5 minutes

### Log aggregation (optional)

For production, route Docker logs to **Papertrail** or **Datadog**:

```yaml
# In docker-compose.yml service definition:
logging:
  driver: syslog
  options:
    syslog-address: "udp://logs.papertrailapp.com:PORT"
    tag: "pepto-{{.Name}}"
```

### Database backups

```bash
# Daily backup script — add to cron
#!/bin/bash
BACKUP_DIR=/opt/pepto/backups
DATE=$(date +%Y%m%d_%H%M%S)

docker compose exec -T postgres \
  pg_dump -U pepto_user -d pepto_db --format=custom \
  > "$BACKUP_DIR/pepto_$DATE.dump"

# Keep last 14 days
find "$BACKUP_DIR" -name "*.dump" -mtime +14 -delete

# Upload to S3
aws s3 cp "$BACKUP_DIR/pepto_$DATE.dump" \
  s3://pepto-backups/postgres/pepto_$DATE.dump
```
