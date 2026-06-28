```
  ██████╗ ███████╗██████╗ ████████╗ ██████╗
  ██╔══██╗██╔════╝██╔══██╗╚══██╔══╝██╔═══██╗
  ██████╔╝█████╗  ██████╔╝   ██║   ██║   ██║
  ██╔═══╝ ██╔══╝  ██╔═══╝    ██║   ██║   ██║
  ██║     ███████╗██║        ██║   ╚██████╔╝
  ╚═╝     ╚══════╝╚═╝        ╚═╝    ╚═════╝
        🐾  Pet Services Marketplace  🐾
```

<div align="center">

[![CI/CD](https://github.com/your-org/pepto/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/your-org/pepto/actions/workflows/ci-cd.yml)
[![codecov](https://codecov.io/gh/your-org/pepto/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/pepto)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-311/)
[![Node 20](https://img.shields.io/badge/node-20-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg?logo=docker)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/postgres-16+PostGIS-336791.svg?logo=postgresql)](https://postgis.net/)

**Connecting pet owners with trusted, local pet care professionals.**

[Live Demo](https://pepto.app) · [API Docs](docs/API.md) · [Report Bug](https://github.com/your-org/pepto/issues) · [Request Feature](https://github.com/your-org/pepto/issues)

</div>

---

## 🐾 What is Pepto?

**Pepto** is a full-stack pet services marketplace that connects pet owners with vetted local professionals — dog walkers, pet sitters, groomers, trainers, and veterinary consultants. Think Airbnb, but for your furry family.

Pet owners can discover verified providers near them on an interactive map, book and pay seamlessly, and leave reviews — all in one place. Providers get a professional profile, booking management dashboard, and automated payouts.

---

## ✨ Features

| Category | Features |
|----------|----------|
| 🗺️ **Discovery** | Map-based search with PostGIS radius queries, filter by service type, rating, price, and availability |
| 📅 **Booking** | Real-time availability calendar, instant or request-to-book, automated confirmations |
| 💳 **Payments** | Stripe-powered checkout, marketplace split payments, automatic provider payouts, refunds |
| 💬 **Messaging** | Real-time in-app chat via Socket.IO between owners and providers |
| ⭐ **Reviews** | Verified booking reviews with rating aggregation |
| 🔔 **Notifications** | Push & in-app notifications for booking updates, messages, and reminders |
| 🐶 **Pet Profiles** | Multi-pet management with medical notes, photos, and breed info |
| 🏪 **Provider Dashboard** | Earnings overview, booking queue, availability management, verification badge |
| 🛡️ **Admin Panel** | Platform stats, user management, provider verification, review moderation |
| 📷 **Photo Uploads** | Cloudinary-backed pet and provider photo uploads with CDN delivery |
| 🔐 **Auth** | JWT authentication with refresh tokens, email verification, password reset |

---

## 🏗️ Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        Browser["🌐 Browser\n(React + Vite)"]
    end

    subgraph Gateway["Gateway Layer"]
        Nginx["🔀 Nginx\n(Reverse Proxy + SSL)"]
    end

    subgraph App["Application Layer"]
        Frontend["⚛️ React Frontend\n(nginx:alpine)"]
        Backend["🐍 Flask API\n(Gunicorn)"]
        Celery["⚙️ Celery Workers\n(Tasks)"]
        Beat["🕐 Celery Beat\n(Scheduler)"]
    end

    subgraph Data["Data Layer"]
        Postgres[("🐘 PostgreSQL\n+ PostGIS")]
        Redis[("🔴 Redis\n(Cache + Queue)")]
    end

    subgraph External["External Services"]
        Stripe["💳 Stripe"]
        Cloudinary["☁️ Cloudinary"]
        Mapbox["🗺️ Mapbox"]
        SMTP["📧 SendGrid"]
        Sentry["🔍 Sentry"]
    end

    Browser --> Nginx
    Nginx -->|"/ SPA"| Frontend
    Nginx -->|"/api/"| Backend
    Nginx -->|"/socket.io/"| Backend
    Backend --> Postgres
    Backend --> Redis
    Celery --> Postgres
    Celery --> Redis
    Beat --> Redis
    Backend --> Stripe
    Backend --> Cloudinary
    Backend --> Mapbox
    Celery --> SMTP
    Backend --> Sentry
```

---

## 🛠️ Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Frontend** | React | 18 | UI framework |
| | Vite | 5 | Build tool & dev server |
| | React Router | 6 | Client-side routing |
| | TanStack Query | 5 | Server state management |
| | Zustand | 4 | Client state management |
| | Tailwind CSS | 3 | Utility-first styling |
| | Socket.IO Client | 4 | Real-time messaging |
| | Mapbox GL JS | 3 | Interactive maps |
| | Stripe.js | latest | Payment UI |
| **Backend** | Python | 3.11 | Language |
| | Flask | 3 | Web framework |
| | Flask-SQLAlchemy | 3 | ORM |
| | Flask-Migrate | 4 | DB migrations (Alembic) |
| | Flask-JWT-Extended | 4 | JWT authentication |
| | Flask-SocketIO | 5 | WebSocket layer |
| | Celery | 5 | Async task queue |
| | Gunicorn | 21 | WSGI server |
| | Marshmallow | 3 | Serialisation/validation |
| | GeoAlchemy2 | 0.14 | PostGIS ORM integration |
| **Database** | PostgreSQL | 16 | Primary relational DB |
| | PostGIS | 3.4 | Geospatial extension |
| | Redis | 7 | Cache + Celery broker |
| **Infrastructure** | Docker | 24+ | Containerisation |
| | Docker Compose | v2 | Local orchestration |
| | Nginx | 1.27 | Reverse proxy + SSL |
| | GitHub Actions | — | CI/CD pipeline |
| **External** | Stripe | — | Payments & payouts |
| | Cloudinary | — | Media storage & CDN |
| | Mapbox | — | Maps & geocoding |
| | SendGrid | — | Transactional email |
| | Sentry | — | Error monitoring |

---

## 🚀 Quick Start

### Prerequisites

Before you begin, make sure you have:

- **Docker Desktop** 24+ — [Install](https://www.docker.com/products/docker-desktop/)
- **Node.js** 20 LTS — [Install](https://nodejs.org/)
- **Python** 3.11 — [Install](https://www.python.org/downloads/)
- **Git** — [Install](https://git-scm.com/)

### 1. Clone the repository

```bash
git clone https://github.com/your-org/pepto.git
cd pepto
```

### 2. Configure environment variables

```bash
# Backend
cp backend/.env.example backend/.env

# Frontend
cp frontend/.env.example frontend/.env.local
```

Edit `backend/.env` with your credentials:

```env
SECRET_KEY=your-super-secret-key-change-me
JWT_SECRET_KEY=another-secret-key-for-jwt
STRIPE_SECRET_KEY=sk_test_your_stripe_key
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
MAPBOX_SECRET_TOKEN=sk.eyJ1...
```

### 3. Start everything with Docker Compose

```bash
docker-compose up --build
```

That's it! Docker will:
1. 🐘 Start PostgreSQL + PostGIS
2. 🔴 Start Redis
3. 🐍 Build and start the Flask API
4. ⚛️ Build and start the React frontend
5. ⚙️ Start Celery worker and beat scheduler
6. 🔀 Start Nginx as the gateway

### 4. Run database migrations (first time)

```bash
docker-compose exec backend flask db upgrade
```

### 5. (Optional) Seed development data

```bash
docker-compose exec backend flask seed-db
```

### Access the application

| Service | URL | Notes |
|---------|-----|-------|
| 🌐 Frontend | http://localhost:3000 | React SPA |
| 🐍 API | http://localhost:5000/api | Flask REST API |
| 🔀 Nginx (prod mode) | http://localhost:80 | Proxied |
| 🐘 PostgreSQL | localhost:5432 | `pepto_user` / `pepto_pass` |
| 🔴 Redis | localhost:6379 | No auth in dev |
| 🌸 Celery Flower | http://localhost:5555 | Task monitor (if enabled) |

---

## 💻 Development Setup

For active development, it's faster to run services individually without Docker.

### Backend (Flask API)

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.\.venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set environment variables
cp .env.example .env
# (edit .env with your credentials)

# Run database migrations
flask db upgrade

# Start the development server (hot-reload)
flask run --debug --port 5000
```

### Frontend (React + Vite)

```bash
cd frontend

# Install dependencies
npm install

# Copy env file
cp .env.example .env.local
# (edit .env.local)

# Start the Vite dev server (HMR enabled)
npm run dev
```

The frontend dev server will proxy `/api/` requests to `http://localhost:5000`.

### Celery Worker (async tasks)

```bash
cd backend
source .venv/bin/activate

# Start worker (requires Redis running)
celery -A celery_app worker --loglevel=debug --concurrency=2

# Start beat scheduler (in a separate terminal)
celery -A celery_app beat --loglevel=debug
```

### Database Migrations

```bash
# Create a new migration after model changes
flask db migrate -m "describe your changes"

# Review the generated file in migrations/versions/

# Apply the migration
flask db upgrade

# Rollback one migration
flask db downgrade -1
```

---

## 📚 API Documentation

Full API reference is in [docs/API.md](docs/API.md).

### Key Endpoint Groups

| Group | Base Path | Description |
|-------|-----------|-------------|
| Auth | `/api/auth/` | Register, login, refresh, reset password |
| Users | `/api/users/` | Profile management, avatar upload |
| Pets | `/api/pets/` | Pet CRUD and photo upload |
| Providers | `/api/providers/` | Search, profiles, availability |
| Services | `/api/services/` | Provider service offerings |
| Bookings | `/api/bookings/` | Create and manage bookings |
| Payments | `/api/payments/` | Stripe integration, webhooks |
| Reviews | `/api/reviews/` | Post and manage reviews |
| Messages | `/api/conversations/` | Real-time messaging |
| Admin | `/api/admin/` | Platform management (admin role) |
| Health | `/api/health` | Service health check |

---

## 🔧 Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ | — | Flask session secret (generate random) |
| `JWT_SECRET_KEY` | ✅ | — | JWT signing key (different from SECRET_KEY) |
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string |
| `REDIS_URL` | ✅ | `redis://localhost:6379/0` | Redis connection string |
| `FLASK_ENV` | ✅ | `development` | `development` or `production` |
| `STRIPE_SECRET_KEY` | ✅ | — | Stripe API secret key |
| `STRIPE_PUBLISHABLE_KEY` | ✅ | — | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | ✅ | — | Stripe webhook signing secret |
| `PLATFORM_FEE_PERCENT` | ✅ | `10` | Marketplace fee percentage |
| `CLOUDINARY_URL` | ✅ | — | Cloudinary full URL with credentials |
| `MAPBOX_SECRET_TOKEN` | ✅ | — | Mapbox server-side API token |
| `MAIL_SERVER` | ✅ | — | SMTP server hostname |
| `MAIL_PORT` | ✅ | `587` | SMTP port |
| `MAIL_USERNAME` | ✅ | — | SMTP username |
| `MAIL_PASSWORD` | ✅ | — | SMTP password |
| `MAIL_DEFAULT_SENDER` | ✅ | — | From address (e.g. `noreply@pepto.app`) |
| `CORS_ORIGINS` | ✅ | `http://localhost:3000` | Allowed CORS origins |
| `SENTRY_DSN` | ⚠️ | — | Sentry DSN for error tracking |
| `LOG_LEVEL` | ❌ | `INFO` | Python logging level |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_BASE_URL` | ✅ | Backend API base URL |
| `VITE_SOCKET_URL` | ✅ | Socket.IO server URL |
| `VITE_STRIPE_PUBLISHABLE_KEY` | ✅ | Stripe publishable key (`pk_...`) |
| `VITE_MAPBOX_TOKEN` | ✅ | Mapbox public token |
| `VITE_CLOUDINARY_CLOUD_NAME` | ✅ | Cloudinary cloud name |
| `VITE_SENTRY_DSN` | ⚠️ | Sentry DSN for frontend error tracking |
| `VITE_ENABLE_CHAT` | ❌ | Feature flag for chat (default: `true`) |

---

## 🧪 Testing

### Backend Tests

```bash
cd backend
source .venv/bin/activate

# Run the full test suite
pytest

# With coverage report
pytest --cov=app --cov-report=html

# Open coverage report
open htmlcov/index.html   # macOS
start htmlcov/index.html  # Windows

# Run a specific test file
pytest tests/test_bookings.py -v

# Run with specific markers
pytest -m "not slow" -v
```

### Frontend Tests

```bash
cd frontend

# Run unit tests (Vitest)
npm test

# Run with UI
npm run test:ui

# E2E tests (Playwright)
npm run test:e2e

# E2E in headed mode (see the browser)
npm run test:e2e:headed
```

### Running Tests with Docker

```bash
# Run backend tests in the container
docker-compose exec backend pytest --cov=app -v

# Run frontend tests in the container
docker-compose exec frontend npm test -- --run
```

---

## 🚢 Deployment

Pepto is designed to deploy to any Docker-compatible platform.

| Platform | Difficulty | Cost | Best For |
|----------|-----------|------|---------|
| [Railway](docs/DEPLOYMENT.md#1-railway-recommended--free-tier) | ⭐ Easy | Free tier available | Early-stage, prototyping |
| [Render](docs/DEPLOYMENT.md#2-render) | ⭐ Easy | Free tier available | Small production traffic |
| [AWS EC2](docs/DEPLOYMENT.md#3-aws-ec2-with-docker-compose) | ⭐⭐⭐ Advanced | ~$30/mo (t3.medium) | Full control, scaling |

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for step-by-step instructions for each platform, including:
- SSL certificate setup with Let's Encrypt / Certbot
- Stripe webhook configuration
- PostGIS database setup
- Celery production configuration
- Monitoring with Sentry and UptimeRobot
- Automated daily database backups

---

## 🤝 Contributing

We welcome contributions from the community!

### Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/pepto.git`
3. **Create a feature branch**: `git checkout -b feature/amazing-feature`
4. **Make your changes** — write tests for new functionality
5. **Run the test suite**: `pytest` (backend) and `npm test` (frontend)
6. **Run linters**: `flake8 .` and `black .` (backend), `npm run lint` (frontend)
7. **Commit**: `git commit -m 'feat: add amazing feature'`
8. **Push**: `git push origin feature/amazing-feature`
9. **Open a Pull Request** against `main`

### Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat:     A new feature
fix:      A bug fix
docs:     Documentation only changes
style:    Formatting, no logic change
refactor: Code change, not a bug fix or feature
test:     Adding tests
chore:    Build process or tooling changes
```

### Code Standards

- **Python**: PEP 8 enforced via `flake8`, formatted with `black` (line length: 120)
- **TypeScript/React**: ESLint + Prettier, functional components only, React Query for server state
- **Tests**: Aim for >70% coverage on new backend code; write at least one test per new endpoint
- **Migrations**: Never manually edit generated migration files; always review before applying

### Reporting Issues

Use GitHub Issues with the appropriate label:
- `bug` — something isn't working
- `enhancement` — feature request
- `documentation` — docs improvement
- `security` — security vulnerability (email security@pepto.app privately)

---

## 📁 Project Structure

```
pepto/
├── backend/                  # Flask API
│   ├── app/
│   │   ├── __init__.py       # App factory
│   │   ├── extensions.py     # SQLAlchemy, JWT, SocketIO, etc.
│   │   ├── models/           # SQLAlchemy models
│   │   ├── api/              # Blueprint route handlers
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── providers.py
│   │   │   ├── bookings.py
│   │   │   ├── payments.py
│   │   │   ├── reviews.py
│   │   │   ├── messages.py
│   │   │   └── admin.py
│   │   ├── tasks/            # Celery async tasks
│   │   ├── utils/            # Helpers, decorators
│   │   └── schemas/          # Marshmallow schemas
│   ├── migrations/           # Alembic migration files
│   ├── tests/                # pytest test suite
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── .env.example
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── gunicorn.conf.py
│   ├── wsgi.py
│   └── celery_app.py
│
├── frontend/                 # React + Vite SPA
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Route-level page components
│   │   ├── hooks/            # Custom React hooks
│   │   ├── stores/           # Zustand state stores
│   │   ├── services/         # API client functions
│   │   ├── utils/            # Shared utilities
│   │   └── types/            # TypeScript type definitions
│   ├── public/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── .env.example
│   ├── nginx.conf            # nginx config for the frontend container
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── nginx/                    # Reverse proxy
│   └── nginx.conf
│
├── docs/                     # Documentation
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── DATABASE.md
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml         # GitHub Actions pipeline
│
├── docker-compose.yml        # Full local stack
├── .gitignore
└── README.md
```

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2026 Pepto Technologies

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

Made with 🐾 by the Pepto team

[pepto.app](https://pepto.app) · [engineering@pepto.app](mailto:engineering@pepto.app)

</div>
